from neo4j import GraphDatabase
import pandas as pd


class ClientLoanFeatureExtractor:
    """
    A class that extracts a row per (Client–Loan), including:
      - Client properties (with Fraud=1 if labeled :FraudCase)
      - Loan properties (status, balance, type)
      - Loaner feature (# of loans with status='rejected')
      - Client node-level features:
         * degree
         * fraud_neighbor_count
         * fraud_loaner_count
         * rejected_loan_count
    """

    def __init__(self, uri, user, password, database=None):
        self.driver = GraphDatabase.driver(uri, auth=(user, password))
        self.database = database

    def close(self):
        self.driver.close()

    def _get_session(self):
        if self.database:
            return self.driver.session(database=self.database)
        else:
            return self.driver.session()

    # ----------------------------------------------------------------
    # PUBLIC METHOD: build a DataFrame, one row per (Client, Loan)
    # ----------------------------------------------------------------
    def extract_client_loan_rows(self):
        """
        1) Build node-level features for each client/fraud node:
           - Basic properties
           - degree
           - fraud_neighbor_count
           - fraud_loaner_count
           - rejected_loan_count
        2) Build a row for each (Client–Loan), capturing loan props,
           plus loaner’s # of rejected loans
        3) Merge the node-level features into each row
        4) Return final DataFrame
        """
        # A) Node-level DataFrame (one row per node)
        node_level_df = self._build_node_level_df()

        # B) Query (Client–Loan–Loaner) for row expansion
        #    This query returns the row-based data for each loan, plus a
        #    "loanerRejectedCount" feature for that loaner
        cl_loan_rows = self._fetch_client_loan_rows()

        # Convert to DataFrame
        df_loans = pd.DataFrame(cl_loan_rows)

        # C) Merge node-level features onto df_loans, matching "client_id"
        final_df = df_loans.merge(node_level_df, how="left", on="client_id")

        # Fill numeric columns with -9999
        numeric_cols = [
            "client_degree",
            "client_fraud_neighbor_count",
            "client_fraud_loaner_count",
            "client_rejected_loan_count",
            "loaner_rejected_count",
            "client_credit_score",
        ]
        for col in numeric_cols:
            if col in final_df.columns:
                final_df[col] = final_df[col].fillna(-9999)

        # Fill everything else with empty
        final_df.fillna("", inplace=True)

        return final_df

    # ----------------------------------------------------------------
    # A) Build Node-Level DataFrame
    # ----------------------------------------------------------------
    def _build_node_level_df(self):
        """
        Return a DataFrame with columns:
          client_id,
          Fraud (0/1),
          client_degree,
          client_fraud_neighbor_count,
          client_fraud_loaner_count,
          client_rejected_loan_count,
          [other basic props like name, phone, etc. if you want]
        """
        # 1) Basic props
        base_df = pd.DataFrame(self._fetch_node_properties())

        # 2) degrees
        df_degrees = pd.DataFrame(self._compute_node_degrees())
        # rename 'degree' -> 'client_degree' to not conflict with anything
        df_degrees.rename(columns={"degree": "client_degree"}, inplace=True)

        base_df = base_df.merge(df_degrees, on="client_id", how="left")

        # 3) fraud neighbors
        df_fraud_nbr = pd.DataFrame(self._compute_fraud_neighbors())
        df_fraud_nbr.rename(
            columns={"fraud_neighbor_count": "client_fraud_neighbor_count"}, inplace=True
        )
        base_df = base_df.merge(df_fraud_nbr, on="client_id", how="left")

        # 4) fraud loaner links
        df_fraud_loaner = pd.DataFrame(self._compute_fraud_loaner_links())
        df_fraud_loaner.rename(
            columns={"fraud_loaner_count": "client_fraud_loaner_count"}, inplace=True
        )
        base_df = base_df.merge(df_fraud_loaner, on="client_id", how="left")

        # 5) rejected loans
        df_rejected = pd.DataFrame(self._compute_rejected_loans())
        df_rejected.rename(
            columns={"rejected_loan_count": "client_rejected_loan_count"}, inplace=True
        )
        base_df = base_df.merge(df_rejected, on="client_id", how="left")

        return base_df

    def _fetch_node_properties(self):
        """
        For each :Client OR :FraudCase node, get basic info + Fraud=1 if labeled :FraudCase.
        Return list of dicts with client_id, name, phone, etc.
        """
        cypher = """
        MATCH (n)
        WHERE n:Client OR n:FraudCase
        RETURN
          ID(n) as internalNeo4jId,
          n.id as client_id,
          n.name as client_name,
          n.phone as client_phone,
          n.email as client_email,
          n.credit_score as client_credit_score,
          n.address as client_address,
          n.suspiciousFlag as client_suspiciousFlag,
          n.move_in_date as client_move_in_date,
          CASE WHEN n:FraudCase THEN 1 ELSE 0 END AS Fraud
        """
        rows = []
        with self._get_session() as session:
            for rec in session.run(cypher):
                cid = rec["client_id"] or str(rec["internalNeo4jId"])
                row = {
                    "client_id": cid,
                    "client_name": rec["client_name"],
                    "client_phone": rec["client_phone"],
                    "client_email": rec["client_email"],
                    "client_credit_score": rec["client_credit_score"],
                    "client_address": rec["client_address"],
                    "client_suspiciousFlag": rec["client_suspiciousFlag"],
                    "client_move_in_date": rec["client_move_in_date"],
                    "Fraud": rec["Fraud"],
                }
                rows.append(row)
        return rows

    # The existing four node-level feature methods:

    def _compute_node_degrees(self):
        """
        For each client node, compute total degree.
        We'll store the results keyed by client_id.
        """
        cypher = """
        MATCH (n)
        WHERE n:Client OR n:FraudCase
        WITH n, size((n)--()) AS deg
        RETURN 
          ID(n) AS internalNeo4jId,
          n.id AS client_id,
          deg AS degree
        """
        out = []
        with self._get_session() as session:
            for record in session.run(cypher):
                cid = record["client_id"] or str(record["internalNeo4jId"])
                out.append({"client_id": cid, "degree": record["degree"]})
        return out

    def _compute_fraud_neighbors(self):
        """
        Count how many adjacent nodes are labeled :FraudCase
        (simple measure of 'proximity to fraud').
        """
        cypher = """
        MATCH (n)
        WHERE n:Client OR n:FraudCase
        OPTIONAL MATCH (n)-[]-(nbr:FraudCase)
        WITH n, count(DISTINCT nbr) AS fraudNeighbors
        RETURN
          ID(n) as internalNeo4jId,
          n.id AS client_id,
          fraudNeighbors
        """
        out = []
        with self._get_session() as session:
            for rec in session.run(cypher):
                cid = rec["client_id"] or str(rec["internalNeo4jId"])
                out.append({"client_id": cid, "fraud_neighbor_count": rec["fraudNeighbors"]})
        return out

    def _compute_fraud_loaner_links(self):
        """
        Count distinct fraudulent loans from the same loaner.
        i.e.
           (n)-[:HAS_LOAN]->(loan)-[:FROM]->(ln:Loaner),
            (ln)<-[:FROM]-(otherLoan:Loan)<-[:HAS_LOAN]-(f:FraudCase)
        """
        cypher = """
        MATCH (n)
        WHERE n:Client OR n:FraudCase
        OPTIONAL MATCH (n)-[:HAS_LOAN]->(l:Loan)-[:FROM]->(ln:Loaner),
                      (ln)<-[:FROM]-(otherLoan:Loan)<-[:HAS_LOAN]-(f:FraudCase)
        WITH n, COUNT(DISTINCT otherLoan) AS fraudLoanerLinks
        RETURN
          ID(n) AS internalNeo4jId,
          n.id AS client_id,
          fraudLoanerLinks
        """
        out = []
        with self._get_session() as session:
            for rec in session.run(cypher):
                cid = rec["client_id"] or str(rec["internalNeo4jId"])
                out.append({"client_id": cid, "fraud_loaner_count": rec["fraudLoanerLinks"]})
        return out

    def _compute_rejected_loans(self):
        """
        Count how many loans this node has with status='rejected'.
        """
        cypher = """
        MATCH (n)
        WHERE n:Client OR n:FraudCase
        OPTIONAL MATCH (n)-[:HAS_LOAN]->(loan:Loan)
        WHERE loan.status = 'rejected'
        WITH n, count(DISTINCT loan) AS rejectedCount
        RETURN
          ID(n) AS internalNeo4jId,
          n.id AS client_id,
          rejectedCount
        """
        out = []
        with self._get_session() as session:
            for rec in session.run(cypher):
                cid = rec["client_id"] or str(rec["internalNeo4jId"])
                out.append({"client_id": cid, "rejected_loan_count": rec["rejectedCount"]})
        return out

    # ----------------------------------------------------------------
    # B) Query for (Client–Loan), plus loaner RejectedCount
    # ----------------------------------------------------------------
    def _fetch_client_loan_rows(self):
        """
        Each row => (client, loan).
        Also includes how many total 'rejected' loans the loaner has.
        """
        cypher = """
        MATCH (c)
        WHERE c:Client OR c:FraudCase
        MATCH (c)-[:HAS_LOAN]->(loan:Loan)-[:FROM]->(ln:Loaner)
        
        // For that loaner, how many total rejected loans exist?
        OPTIONAL MATCH (ln)<-[:FROM]-(anyLoan:Loan)
        WHERE anyLoan.status = 'rejected'
        WITH c, loan, ln, COUNT(DISTINCT anyLoan) AS loanerRejectedCount
        
        RETURN
          // client info
          ID(c) AS clientNeo4jId,
          c.id AS client_id,
          
          // loan
          loan.id AS loan_id,
          loan.type AS loan_type,
          loan.balance AS loan_balance,
          loan.status AS loan_status,
          
          // loaner feature
          loanerRejectedCount AS loaner_rejected_count
        """
        rows = []
        with self._get_session() as session:
            res = session.run(cypher)
            for rec in res:
                row = {
                    "client_id": rec["client_id"] or str(rec["clientNeo4jId"]),
                    "loan_id": rec["loan_id"] or "",
                    "loan_type": rec["loan_type"] or "",
                    "loan_balance": rec["loan_balance"],
                    "loan_status": rec["loan_status"] or "",
                    "loaner_rejected_count": rec["loaner_rejected_count"] or 0,
                }
                rows.append(row)
        return rows


def update_neo4j_predictions(scored_df, best_model):
    # Connect to Neo4j
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    session = driver.session(database=NEO4J_DATABASE)

    # MERGE a single model node
    model_id = best_model.id
    model_type = best_model.model_type
    session.run(
        """
    MERGE (m:DataRobotModel {id:$model_id})
    ON CREATE SET m.model_type=$model_type
    """,
        model_id=model_id,
        model_type=model_type,
    )

    # For each row, create PredictedFraud node + link to model + Loan
    for idx, row in scored_df.iterrows():
        loan_id = row["loan_id"]
        prob = row["pred_fraud_probability"]
        top_feat = row["top_feature"]
        top_feat_val = row["top_feature_value"]
        top_feat_qual_strgth = row["top_feat_qual_strgth"]
        flagged = row["flagged_as_fraud"]

        cypher = """
        MATCH (ln:Loan {id:$loan_id})
        MERGE (pf:PredictedFraud {uniqueKey:$unique_key})
        SET pf.score=$prob,
            pf.topFeature=$top_feat,
            pf.topFeatureValue=$top_feat_val,
            pf.topFeatureQualStrgth=$top_feat_qual_strgth,
            pf.isFlagged=$flagged,
            pf.createdAt=timestamp()
        MERGE (ln)-[:HAS_PREDICTION]->(pf)

        WITH pf
        MATCH (m:DataRobotModel {id:$model_id})
        MERGE (pf)-[:USING_MODEL]->(m)
        """
        unique_key = f"{loan_id}-pred-{model_id}-{idx}"
        session.run(
            cypher,
            loan_id=loan_id,
            unique_key=unique_key,
            prob=prob,
            top_feat=top_feat or "",
            top_feat_val=top_feat_val or 0.0,
            top_feat_qual_strgth=top_feat_qual_strgth or "",
            flagged=int(flagged),
            model_id=model_id,
        )
    session.close()
    driver.close()
    print("\nNeo4j updated with predicted fraud nodes on holdout loans.")


# ----------------------------------------------
# Example usage
# ----------------------------------------------
if __name__ == "__main__":
    uri = "bolt://localhost:7687"
    user = "neo4j"
    password = "password"
    database = "neo4j"  # or "neo4j" if multi-db

    extractor = ClientLoanFeatureExtractor(uri, user, password, database)
    df = extractor.extract_client_loan_rows()

    print(df.head(10))

    # Save to CSV for DataRobot
    df.to_csv("client_loan_with_node_features.csv", index=False)

    extractor.close()
    print("Done! Wrote client-loan table to client_loan_with_node_features.csv")
