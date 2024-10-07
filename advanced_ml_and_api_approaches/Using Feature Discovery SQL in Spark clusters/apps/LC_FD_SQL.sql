
/* ------------------------------ */

/* -- `DR_PRIMARY_TABLE (view)` -- */

CREATE OR REPLACE TEMPORARY VIEW `DR_PRIMARY_TABLE (view)` AS 

/*
BLOCK START -- Create "DR_PRIMARY_TABLE" table with prediction point

DESCRIPTION:
- Create internal prediction point in the primary table.
- Apply conversion to timestamp and round off if necessary
*/

SELECT

  *,
  
  to_timestamp(
    from_unixtime(
      floor(
        unix_timestamp(
          `SAFER_CUTOFF_598d7e6ae89bde0eadd7456a`
        ) / 60.0
      ) * 60.0
    ), 'yyyy-MM-dd HH:mm:ss'
  )
  AS `SAFER_CUTOFF_598d7e6ae89bde0eadd7456a_1_MINUTE`

FROM (

  SELECT
  
    *,
    
    TO_TIMESTAMP(
      `date`, "yyyy-MM-dd"
    )
    AS `SAFER_CUTOFF_598d7e6ae89bde0eadd7456a`
  
  FROM `DR_PRIMARY_TABLE`
  
) AS `DR_PRIMARY_TABLE`


/*
BLOCK END -- Create "DR_PRIMARY_TABLE" table with prediction point
*/


/* ------------------------------ */

/* -- `filtered LC_profile (by {"CustomerID"}-{"CustomerID"}) (view)` -- */

CREATE OR REPLACE TEMPORARY VIEW `filtered LC_profile (by {"CustomerID"}-{"CustomerID"}) (view)` AS 

/*
BLOCK START -- Create filtered "LC_profile" table

DESCRIPTION:
- Inner join "LC_profile (by {"CustomerID"}-{"CustomerID"})" table to the primary table.
  This will keep only records in "LC_profile (by {"CustomerID"}-{"CustomerID"})" table that can be associated to the primary table.
*/

SELECT

  *

FROM (

  SELECT
  
    *,
    
    RANK() OVER (
      PARTITION BY `CustomerID` ORDER BY `SAFER_ROW_HASH_598d7e6ae89bde0eadd7456d` DESC, `SAFER_ROW_ID_598d7e6ae89bde0eadd7456c` DESC
    )
    AS `SAFER_RANK_598d7e6ae89bde0eadd74568`
  
  FROM (
  
    SELECT DISTINCT
    
      `LC_profile (by {"CustomerID"}-{"CustomerID"})`.*
    
    FROM (
    
      SELECT DISTINCT
      
        `DR_PRIMARY_TABLE`.`CustomerID`
      
      FROM (
      
        `DR_PRIMARY_TABLE (view)` AS `DR_PRIMARY_TABLE`
        
      )
      
    ) AS `DR_PRIMARY_TABLE`
    
    INNER JOIN (
    
      /*
      DESCRIPTION:
      - Add Row ID and Row Hash to "LC_profile" table to generate reproducible results.
        Row ID is consistent with row orders for a single-file input source.
        Row Hash provides best-effort consistency for multi-file or database input sources.
      */
      
      SELECT
      
        *,
        
        monotonically_increasing_id()
        AS `SAFER_ROW_ID_598d7e6ae89bde0eadd7456c`,
        
        hash(
          `CustomerID`, `addr_state`, `annual_inc`, `emp_length`, `emp_title`, `funded_amnt`, `grade`, `home_ownership`, `installment`, `int_rate`, `loan_amnt`, `purpose`, `sub_grade`, `term`, `verification_status`, `zip_code`
        )
        AS `SAFER_ROW_HASH_598d7e6ae89bde0eadd7456d`
      
      FROM `LC_profile`
      
    ) AS `LC_profile (by {"CustomerID"}-{"CustomerID"})`
    
    ON
    
      `DR_PRIMARY_TABLE`.`CustomerID` = `LC_profile (by {"CustomerID"}-{"CustomerID"})`.`CustomerID`
    
  )
  
)

WHERE

  SAFER_RANK_598d7e6ae89bde0eadd74568 = 1

/*
BLOCK END -- Create filtered "LC_profile" table
*/


/* ------------------------------ */

/* -- `featurized LC_profile (by {"CustomerID"}-{"CustomerID"}) (view)` -- */

CREATE OR REPLACE TEMPORARY VIEW `featurized LC_profile (by {"CustomerID"}-{"CustomerID"}) (view)` AS 

/*
BLOCK START -- Create "LC_profile (by {"CustomerID"}-{"CustomerID"})" table with engineered features

DESCRIPTION:
- Apply transformations on columns.
*/

SELECT

  `LC_profile (by {"CustomerID"}-{"CustomerID"})`.`CustomerID`,
  
  `LC_profile (by {"CustomerID"}-{"CustomerID"})`.`addr_state`,
  
  `LC_profile (by {"CustomerID"}-{"CustomerID"})`.`annual_inc`,
  
  `LC_profile (by {"CustomerID"}-{"CustomerID"})`.`emp_length`,
  
  `LC_profile (by {"CustomerID"}-{"CustomerID"})`.`emp_title`,
  
  `LC_profile (by {"CustomerID"}-{"CustomerID"})`.`funded_amnt`,
  
  `LC_profile (by {"CustomerID"}-{"CustomerID"})`.`grade`,
  
  `LC_profile (by {"CustomerID"}-{"CustomerID"})`.`home_ownership`,
  
  `LC_profile (by {"CustomerID"}-{"CustomerID"})`.`installment`,
  
  `LC_profile (by {"CustomerID"}-{"CustomerID"})`.`int_rate`,
  
  `LC_profile (by {"CustomerID"}-{"CustomerID"})`.`loan_amnt`,
  
  `LC_profile (by {"CustomerID"}-{"CustomerID"})`.`purpose`,
  
  `LC_profile (by {"CustomerID"}-{"CustomerID"})`.`sub_grade`,
  
  `LC_profile (by {"CustomerID"}-{"CustomerID"})`.`term`,
  
  `LC_profile (by {"CustomerID"}-{"CustomerID"})`.`verification_status`,
  
  `LC_profile (by {"CustomerID"}-{"CustomerID"})`.`zip_code`,
  
  SIZE(
    SPLIT(
      `LC_profile (by {"CustomerID"}-{"CustomerID"})`.`emp_title`, " "
    )
  )
  AS `LC_profile[emp_title] (word count)`,
  
  `LC_profile (by {"CustomerID"}-{"CustomerID"})`.SAFER_ROW_ID_598d7e6ae89bde0eadd7456c,
  
  `LC_profile (by {"CustomerID"}-{"CustomerID"})`.SAFER_ROW_HASH_598d7e6ae89bde0eadd7456d

FROM (

  `filtered LC_profile (by {"CustomerID"}-{"CustomerID"}) (view)` AS `LC_profile (by {"CustomerID"}-{"CustomerID"})`
  
)

/*
BLOCK END -- Create "LC_profile (by {"CustomerID"}-{"CustomerID"})" table with engineered features
*/


/* ------------------------------ */

/* -- `featurized DR_PRIMARY_TABLE (lookup only) (view)` -- */

CREATE OR REPLACE TEMPORARY VIEW `featurized DR_PRIMARY_TABLE (lookup only) (view)` AS 

/*
BLOCK START -- Create "DR_PRIMARY_TABLE" table with engineered features from lookup tables

DESCRIPTION:
- Left join "LC_profile (by {"CustomerID"}-{"CustomerID"})" table to "DR_PRIMARY_TABLE" table.
*/

SELECT

  `DR_PRIMARY_TABLE`.`CustomerID`,
  
  `DR_PRIMARY_TABLE`.`BadLoan`,
  
  `DR_PRIMARY_TABLE`.`date`,
  
  `DR_PRIMARY_TABLE`.`SAFER_CUTOFF_598d7e6ae89bde0eadd7456a_1_MINUTE`,
  
  `DR_PRIMARY_TABLE`.`SAFER_CUTOFF_598d7e6ae89bde0eadd7456a`,
  
  `LC_profile (by {"CustomerID"}-{"CustomerID"})`.`addr_state`
  AS `LC_profile[addr_state]`,
  
  dr_numeric_rounding(
    `LC_profile (by {"CustomerID"}-{"CustomerID"})`.`annual_inc`
  )
  AS `LC_profile[annual_inc]`,
  
  `LC_profile (by {"CustomerID"}-{"CustomerID"})`.`emp_length`
  AS `LC_profile[emp_length]`,
  
  `LC_profile (by {"CustomerID"}-{"CustomerID"})`.`emp_title`
  AS `LC_profile[emp_title]`,
  
  `LC_profile (by {"CustomerID"}-{"CustomerID"})`.`funded_amnt`
  AS `LC_profile[funded_amnt]`,
  
  `LC_profile (by {"CustomerID"}-{"CustomerID"})`.`grade`
  AS `LC_profile[grade]`,
  
  `LC_profile (by {"CustomerID"}-{"CustomerID"})`.`home_ownership`
  AS `LC_profile[home_ownership]`,
  
  dr_numeric_rounding(
    `LC_profile (by {"CustomerID"}-{"CustomerID"})`.`installment`
  )
  AS `LC_profile[installment]`,
  
  dr_numeric_rounding(
    `LC_profile (by {"CustomerID"}-{"CustomerID"})`.`int_rate`
  )
  AS `LC_profile[int_rate]`,
  
  `LC_profile (by {"CustomerID"}-{"CustomerID"})`.`loan_amnt`
  AS `LC_profile[loan_amnt]`,
  
  `LC_profile (by {"CustomerID"}-{"CustomerID"})`.`purpose`
  AS `LC_profile[purpose]`,
  
  `LC_profile (by {"CustomerID"}-{"CustomerID"})`.`sub_grade`
  AS `LC_profile[sub_grade]`,
  
  `LC_profile (by {"CustomerID"}-{"CustomerID"})`.`term`
  AS `LC_profile[term]`,
  
  `LC_profile (by {"CustomerID"}-{"CustomerID"})`.`verification_status`
  AS `LC_profile[verification_status]`,
  
  `LC_profile (by {"CustomerID"}-{"CustomerID"})`.`zip_code`
  AS `LC_profile[zip_code]`,
  
  dr_numeric_rounding(
    `LC_profile (by {"CustomerID"}-{"CustomerID"})`.`LC_profile[emp_title] (word count)`
  )
  AS `LC_profile[emp_title] (word count)`

FROM (

  `DR_PRIMARY_TABLE (view)` AS `DR_PRIMARY_TABLE`
  
)
LEFT JOIN (

  `featurized LC_profile (by {"CustomerID"}-{"CustomerID"}) (view)` AS `LC_profile (by {"CustomerID"}-{"CustomerID"})`
  
) AS `LC_profile (by {"CustomerID"}-{"CustomerID"})`

ON

  `DR_PRIMARY_TABLE`.`CustomerID` = `LC_profile (by {"CustomerID"}-{"CustomerID"})`.`CustomerID`

/*
BLOCK END -- Create "DR_PRIMARY_TABLE" table with engineered features from lookup tables
*/


/* ------------------------------ */

/* -- `filtered LC_transactions (by {"CustomerID"}-{"CustomerID"}) (30 days) (view)` -- */

CREATE OR REPLACE TEMPORARY VIEW `filtered LC_transactions (by {"CustomerID"}-{"CustomerID"}) (30 days) (view)` AS 

/*
BLOCK START -- Create filtered "LC_transactions" table (30 days)

DESCRIPTION:
- Inner join "LC_transactions (by {"CustomerID"}-{"CustomerID"})" table to the primary table.
  This will keep only records in "LC_transactions (by {"CustomerID"}-{"CustomerID"})" table that can be associated to the primary table.
- Use prediction point rounded to the most recent 1 minute.
- Get records within the feature derivation window at the prediction point.
- Include only rows within the 30 days Feature Derivation Window (FDW) before prediction point.
*/

SELECT DISTINCT

  `LC_transactions (by {"CustomerID"}-{"CustomerID"})`.*,
  
  `SAFER_CUTOFF_598d7e6ae89bde0eadd7456a`

FROM (

  SELECT
  
    *,
    
    WINDOW(
      `SAFER_CUTOFF_598d7e6ae89bde0eadd7456a`, "30 days"
    ).start
    AS `SAFER_WINDOW_598d7e6ae89bde0eadd7456b`,
    
    WINDOW(
      `SAFER_CUTOFF_598d7e6ae89bde0eadd7456a`, "30 days"
    ).start - INTERVAL 30 days
    AS `SAFER_WINDOW_MINUS_598d7e6ae89bde0eadd7456b`
  
  FROM (
  
    SELECT DISTINCT
    
      `DR_PRIMARY_TABLE`.`CustomerID`,
      
      `DR_PRIMARY_TABLE`.`SAFER_CUTOFF_598d7e6ae89bde0eadd7456a_1_MINUTE`,
      
      `DR_PRIMARY_TABLE`.`SAFER_CUTOFF_598d7e6ae89bde0eadd7456a_1_MINUTE`
      AS `SAFER_CUTOFF_598d7e6ae89bde0eadd7456a`
    
    FROM (
    
      `featurized DR_PRIMARY_TABLE (lookup only) (view)` AS `DR_PRIMARY_TABLE`
      
    )
    
  ) AS `DR_PRIMARY_TABLE`
  
  
) AS `DR_PRIMARY_TABLE`

INNER JOIN (

  SELECT
  
    *,
    
    WINDOW(
      `Date`, "30 days"
    ).start
    AS `SAFER_WINDOW_598d7e6ae89bde0eadd7456b`
  
  FROM (
  
    /*
    DESCRIPTION:
    - Add Row ID and Row Hash to "LC_transactions" table to generate reproducible results.
      Row ID is consistent with row orders for a single-file input source.
      Row Hash provides best-effort consistency for multi-file or database input sources.
    */
    
    SELECT
    
      *,
      
      monotonically_increasing_id()
      AS `SAFER_ROW_ID_598d7e6ae89bde0eadd7456c`,
      
      hash(
        `AccountID`, `Amount`, `CustomerID`, `Date`, `Description`
      )
      AS `SAFER_ROW_HASH_598d7e6ae89bde0eadd7456d`
    
    FROM (
    
      /*
      DESCRIPTION:
      - Apply type casting on applicable columns in "LC_transactions (by {"CustomerID"}-{"CustomerID"})" table
      */
      
      SELECT
      
        `AccountID`,
        
        `Amount`,
        
        `CustomerID`,
        
        TO_TIMESTAMP(
          `Date`, "yyyy-MM-dd"
        )
        AS `Date`,
        
        `Description`
      
      FROM `LC_transactions`
      
    ) AS `LC_transactions`
    
    
  )
  
) AS `LC_transactions (by {"CustomerID"}-{"CustomerID"})`

ON

  `DR_PRIMARY_TABLE`.`CustomerID` = `LC_transactions (by {"CustomerID"}-{"CustomerID"})`.`CustomerID` AND
  (
  
    `DR_PRIMARY_TABLE`.`SAFER_WINDOW_598d7e6ae89bde0eadd7456b` = `LC_transactions (by {"CustomerID"}-{"CustomerID"})`.`SAFER_WINDOW_598d7e6ae89bde0eadd7456b` OR `DR_PRIMARY_TABLE`.`SAFER_WINDOW_MINUS_598d7e6ae89bde0eadd7456b` = `LC_transactions (by {"CustomerID"}-{"CustomerID"})`.`SAFER_WINDOW_598d7e6ae89bde0eadd7456b`
  
  )

WHERE

  `LC_transactions (by {"CustomerID"}-{"CustomerID"})`.`Date` < `DR_PRIMARY_TABLE`.`SAFER_CUTOFF_598d7e6ae89bde0eadd7456a_1_MINUTE` AND
  `LC_transactions (by {"CustomerID"}-{"CustomerID"})`.`Date` >= (`DR_PRIMARY_TABLE`.`SAFER_CUTOFF_598d7e6ae89bde0eadd7456a_1_MINUTE` - INTERVAL 30 days)

/*
BLOCK END -- Create filtered "LC_transactions" table (30 days)
*/


/* ------------------------------ */

/* -- `filtered LC_transactions (by {"CustomerID"}-{"CustomerID"}) (1 week) (view)` -- */

CREATE OR REPLACE TEMPORARY VIEW `filtered LC_transactions (by {"CustomerID"}-{"CustomerID"}) (1 week) (view)` AS 

/*
BLOCK START -- Create filtered "LC_transactions" table (1 week)

DESCRIPTION:
- Inner join "LC_transactions (by {"CustomerID"}-{"CustomerID"})" table to the primary table.
  This will keep only records in "LC_transactions (by {"CustomerID"}-{"CustomerID"})" table that can be associated to the primary table.
- Use prediction point rounded to the most recent 1 minute.
- Get records within the feature derivation window at the prediction point.
- Include only rows within the 1 week Feature Derivation Window (FDW) before prediction point.
*/

SELECT DISTINCT

  `LC_transactions (by {"CustomerID"}-{"CustomerID"})`.*,
  
  `SAFER_CUTOFF_598d7e6ae89bde0eadd7456a`

FROM (

  SELECT
  
    *,
    
    WINDOW(
      `SAFER_CUTOFF_598d7e6ae89bde0eadd7456a`, "7 days"
    ).start
    AS `SAFER_WINDOW_598d7e6ae89bde0eadd7456b`,
    
    WINDOW(
      `SAFER_CUTOFF_598d7e6ae89bde0eadd7456a`, "7 days"
    ).start - INTERVAL 7 days
    AS `SAFER_WINDOW_MINUS_598d7e6ae89bde0eadd7456b`
  
  FROM (
  
    SELECT DISTINCT
    
      `DR_PRIMARY_TABLE`.`CustomerID`,
      
      `DR_PRIMARY_TABLE`.`SAFER_CUTOFF_598d7e6ae89bde0eadd7456a_1_MINUTE`,
      
      `DR_PRIMARY_TABLE`.`SAFER_CUTOFF_598d7e6ae89bde0eadd7456a_1_MINUTE`
      AS `SAFER_CUTOFF_598d7e6ae89bde0eadd7456a`
    
    FROM (
    
      `featurized DR_PRIMARY_TABLE (lookup only) (view)` AS `DR_PRIMARY_TABLE`
      
    )
    
  ) AS `DR_PRIMARY_TABLE`
  
  
) AS `DR_PRIMARY_TABLE`

INNER JOIN (

  SELECT
  
    *,
    
    WINDOW(
      `Date`, "7 days"
    ).start
    AS `SAFER_WINDOW_598d7e6ae89bde0eadd7456b`
  
  FROM (
  
    /*
    DESCRIPTION:
    - Add Row ID and Row Hash to "LC_transactions" table to generate reproducible results.
      Row ID is consistent with row orders for a single-file input source.
      Row Hash provides best-effort consistency for multi-file or database input sources.
    */
    
    SELECT
    
      *,
      
      monotonically_increasing_id()
      AS `SAFER_ROW_ID_598d7e6ae89bde0eadd7456c`,
      
      hash(
        `AccountID`, `Amount`, `CustomerID`, `Date`, `Description`
      )
      AS `SAFER_ROW_HASH_598d7e6ae89bde0eadd7456d`
    
    FROM (
    
      /*
      DESCRIPTION:
      - Apply type casting on applicable columns in "LC_transactions (by {"CustomerID"}-{"CustomerID"})" table
      */
      
      SELECT
      
        `AccountID`,
        
        `Amount`,
        
        `CustomerID`,
        
        TO_TIMESTAMP(
          `Date`, "yyyy-MM-dd"
        )
        AS `Date`,
        
        `Description`
      
      FROM `LC_transactions`
      
    ) AS `LC_transactions`
    
    
  )
  
) AS `LC_transactions (by {"CustomerID"}-{"CustomerID"})`

ON

  `DR_PRIMARY_TABLE`.`CustomerID` = `LC_transactions (by {"CustomerID"}-{"CustomerID"})`.`CustomerID` AND
  (
  
    `DR_PRIMARY_TABLE`.`SAFER_WINDOW_598d7e6ae89bde0eadd7456b` = `LC_transactions (by {"CustomerID"}-{"CustomerID"})`.`SAFER_WINDOW_598d7e6ae89bde0eadd7456b` OR `DR_PRIMARY_TABLE`.`SAFER_WINDOW_MINUS_598d7e6ae89bde0eadd7456b` = `LC_transactions (by {"CustomerID"}-{"CustomerID"})`.`SAFER_WINDOW_598d7e6ae89bde0eadd7456b`
  
  )

WHERE

  `LC_transactions (by {"CustomerID"}-{"CustomerID"})`.`Date` < `DR_PRIMARY_TABLE`.`SAFER_CUTOFF_598d7e6ae89bde0eadd7456a_1_MINUTE` AND
  `LC_transactions (by {"CustomerID"}-{"CustomerID"})`.`Date` >= (`DR_PRIMARY_TABLE`.`SAFER_CUTOFF_598d7e6ae89bde0eadd7456a_1_MINUTE` - INTERVAL 1 weeks)

/*
BLOCK END -- Create filtered "LC_transactions" table (1 week)
*/


/* ------------------------------ */

/* -- `featurized LC_transactions (by {"CustomerID"}-{"CustomerID"}) (30 days) (view)` -- */

CREATE OR REPLACE TEMPORARY VIEW `featurized LC_transactions (by {"CustomerID"}-{"CustomerID"}) (30 days) (view)` AS 

/*
BLOCK START -- Create "LC_transactions (by {"CustomerID"}-{"CustomerID"})" table with engineered features (30 days)

DESCRIPTION:
- Apply transformations on columns.
*/

SELECT

  `LC_transactions (by {"CustomerID"}-{"CustomerID"})`.`AccountID`,
  
  `LC_transactions (by {"CustomerID"}-{"CustomerID"})`.`Amount`,
  
  `LC_transactions (by {"CustomerID"}-{"CustomerID"})`.`CustomerID`,
  
  `LC_transactions (by {"CustomerID"}-{"CustomerID"})`.`Date`,
  
  `LC_transactions (by {"CustomerID"}-{"CustomerID"})`.`Description`,
  
  `LC_transactions (by {"CustomerID"}-{"CustomerID"})`.`SAFER_CUTOFF_598d7e6ae89bde0eadd7456a`,
  
  (
    UNIX_TIMESTAMP(
      `LC_transactions (by {"CustomerID"}-{"CustomerID"})`.`SAFER_CUTOFF_598d7e6ae89bde0eadd7456a`
    ) - UNIX_TIMESTAMP(
      `LC_transactions (by {"CustomerID"}-{"CustomerID"})`.`Date`
    )
  ) / 86400
  AS `date (days from LC_transactions[Date])`,
  
  (
    UNIX_TIMESTAMP(
      `LC_transactions (by {"CustomerID"}-{"CustomerID"})`.`Date`
    ) - UNIX_TIMESTAMP(
      LAG(
        `LC_transactions (by {"CustomerID"}-{"CustomerID"})`.`Date`, 1
      ) OVER (
        PARTITION BY `LC_transactions (by {"CustomerID"}-{"CustomerID"})`.`CustomerID`, `LC_transactions (by {"CustomerID"}-{"CustomerID"})`.`SAFER_CUTOFF_598d7e6ae89bde0eadd7456a` ORDER BY `LC_transactions (by {"CustomerID"}-{"CustomerID"})`.`Date`, `LC_transactions (by {"CustomerID"}-{"CustomerID"})`.SAFER_ROW_HASH_598d7e6ae89bde0eadd7456d ASC
      )
    )
  ) / 86400
  AS `LC_transactions (days since previous event by CustomerID)`,
  
  CAST(
    DATE_FORMAT(
      `LC_transactions (by {"CustomerID"}-{"CustomerID"})`.`Date`, "u"
    ) - 1 AS INT
  )
  AS `LC_transactions[Date] (Day of Week)`,
  
  DAYOFMONTH(
    `LC_transactions (by {"CustomerID"}-{"CustomerID"})`.`Date`
  )
  AS `LC_transactions[Date] (Day of Month)`,
  
  HOUR(
    `LC_transactions (by {"CustomerID"}-{"CustomerID"})`.`Date`
  )
  AS `LC_transactions[Date] (Hour of Day)`,
  
  dr_regexp_match_all(
    LOWER(
      `LC_transactions (by {"CustomerID"}-{"CustomerID"})`.`AccountID`
    ), "[\\pL\\pN\\_]{2,}"
  )
  AS `LC_transactions[AccountID] (token array)`,
  
  SIZE(
    SPLIT(
      `LC_transactions (by {"CustomerID"}-{"CustomerID"})`.`AccountID`, " "
    )
  )
  AS `LC_transactions[AccountID] (word count)`,
  
  dr_list_to_map_cnt(
    dr_regexp_match_all(
      LOWER(
        `LC_transactions (by {"CustomerID"}-{"CustomerID"})`.`AccountID`
      ), "[\\pL\\pN\\_]{2,}"
    )
  )
  AS `LC_transactions[AccountID] (token counts)`,
  
  `LC_transactions (by {"CustomerID"}-{"CustomerID"})`.SAFER_ROW_ID_598d7e6ae89bde0eadd7456c,
  
  `LC_transactions (by {"CustomerID"}-{"CustomerID"})`.SAFER_ROW_HASH_598d7e6ae89bde0eadd7456d

FROM (

  `filtered LC_transactions (by {"CustomerID"}-{"CustomerID"}) (30 days) (view)` AS `LC_transactions (by {"CustomerID"}-{"CustomerID"})`
  
)

DISTRIBUTE BY

  `CustomerID`,
  `SAFER_CUTOFF_598d7e6ae89bde0eadd7456a`,
  SAFER_ROW_ID_598d7e6ae89bde0eadd7456c

/*
BLOCK END -- Create "LC_transactions (by {"CustomerID"}-{"CustomerID"})" table with engineered features (30 days)
*/


/* ------------------------------ */

/* -- `featurized LC_transactions (by {"CustomerID"}-{"CustomerID"}) (1 week) (view)` -- */

CREATE OR REPLACE TEMPORARY VIEW `featurized LC_transactions (by {"CustomerID"}-{"CustomerID"}) (1 week) (view)` AS 

/*
BLOCK START -- Create "LC_transactions (by {"CustomerID"}-{"CustomerID"})" table with engineered features (1 week)

DESCRIPTION:
- Apply transformations on columns.
*/

SELECT

  `LC_transactions (by {"CustomerID"}-{"CustomerID"})`.`AccountID`,
  
  `LC_transactions (by {"CustomerID"}-{"CustomerID"})`.`Amount`,
  
  `LC_transactions (by {"CustomerID"}-{"CustomerID"})`.`CustomerID`,
  
  `LC_transactions (by {"CustomerID"}-{"CustomerID"})`.`Date`,
  
  `LC_transactions (by {"CustomerID"}-{"CustomerID"})`.`Description`,
  
  `LC_transactions (by {"CustomerID"}-{"CustomerID"})`.`SAFER_CUTOFF_598d7e6ae89bde0eadd7456a`,
  
  (
    UNIX_TIMESTAMP(
      `LC_transactions (by {"CustomerID"}-{"CustomerID"})`.`SAFER_CUTOFF_598d7e6ae89bde0eadd7456a`
    ) - UNIX_TIMESTAMP(
      `LC_transactions (by {"CustomerID"}-{"CustomerID"})`.`Date`
    )
  ) / 86400
  AS `date (days from LC_transactions[Date])`,
  
  (
    UNIX_TIMESTAMP(
      `LC_transactions (by {"CustomerID"}-{"CustomerID"})`.`Date`
    ) - UNIX_TIMESTAMP(
      LAG(
        `LC_transactions (by {"CustomerID"}-{"CustomerID"})`.`Date`, 1
      ) OVER (
        PARTITION BY `LC_transactions (by {"CustomerID"}-{"CustomerID"})`.`CustomerID`, `LC_transactions (by {"CustomerID"}-{"CustomerID"})`.`SAFER_CUTOFF_598d7e6ae89bde0eadd7456a` ORDER BY `LC_transactions (by {"CustomerID"}-{"CustomerID"})`.`Date`, `LC_transactions (by {"CustomerID"}-{"CustomerID"})`.SAFER_ROW_HASH_598d7e6ae89bde0eadd7456d ASC
      )
    )
  ) / 86400
  AS `LC_transactions (days since previous event by CustomerID)`,
  
  CAST(
    DATE_FORMAT(
      `LC_transactions (by {"CustomerID"}-{"CustomerID"})`.`Date`, "u"
    ) - 1 AS INT
  )
  AS `LC_transactions[Date] (Day of Week)`,
  
  DAYOFMONTH(
    `LC_transactions (by {"CustomerID"}-{"CustomerID"})`.`Date`
  )
  AS `LC_transactions[Date] (Day of Month)`,
  
  HOUR(
    `LC_transactions (by {"CustomerID"}-{"CustomerID"})`.`Date`
  )
  AS `LC_transactions[Date] (Hour of Day)`,
  
  dr_regexp_match_all(
    LOWER(
      `LC_transactions (by {"CustomerID"}-{"CustomerID"})`.`AccountID`
    ), "[\\pL\\pN\\_]{2,}"
  )
  AS `LC_transactions[AccountID] (token array)`,
  
  SIZE(
    SPLIT(
      `LC_transactions (by {"CustomerID"}-{"CustomerID"})`.`AccountID`, " "
    )
  )
  AS `LC_transactions[AccountID] (word count)`,
  
  dr_list_to_map_cnt(
    dr_regexp_match_all(
      LOWER(
        `LC_transactions (by {"CustomerID"}-{"CustomerID"})`.`AccountID`
      ), "[\\pL\\pN\\_]{2,}"
    )
  )
  AS `LC_transactions[AccountID] (token counts)`,
  
  `LC_transactions (by {"CustomerID"}-{"CustomerID"})`.SAFER_ROW_ID_598d7e6ae89bde0eadd7456c,
  
  `LC_transactions (by {"CustomerID"}-{"CustomerID"})`.SAFER_ROW_HASH_598d7e6ae89bde0eadd7456d

FROM (

  `filtered LC_transactions (by {"CustomerID"}-{"CustomerID"}) (1 week) (view)` AS `LC_transactions (by {"CustomerID"}-{"CustomerID"})`
  
)

DISTRIBUTE BY

  `CustomerID`,
  `SAFER_CUTOFF_598d7e6ae89bde0eadd7456a`,
  SAFER_ROW_ID_598d7e6ae89bde0eadd7456c

/*
BLOCK END -- Create "LC_transactions (by {"CustomerID"}-{"CustomerID"})" table with engineered features (1 week)
*/


/* ------------------------------ */

/* -- `featurized LC_transactions (aggregated by {"CustomerID"}-{"CustomerID"}) (FDW 1 week) (1 week) (view)` -- */

CREATE OR REPLACE TEMPORARY VIEW `featurized LC_transactions (aggregated by {"CustomerID"}-{"CustomerID"}) (FDW 1 week) (1 week) (view)` AS 

/*
BLOCK START -- Create "LC_transactions (aggregated by {"CustomerID"}-{"CustomerID"}) (FDW 1 week)" table with engineered features (1 week)

DESCRIPTION:
- Aggregate columns over group keys: `CustomerID`, `SAFER_CUTOFF_598d7e6ae89bde0eadd7456a`
- Apply transformations on columns.
*/

SELECT

  COUNT(
    *
  )
  AS `LC_transactions (1 week count)`,
  
  PERCENTILE(
    CASE WHEN isnan(
      `LC_transactions (by {"CustomerID"}-{"CustomerID"})`.`Amount`
    ) THEN null ELSE `LC_transactions (by {"CustomerID"}-{"CustomerID"})`.`Amount` END, 0.5
  )
  AS `LC_transactions[Amount] (1 week median)`,
  
  SUM(
    CASE WHEN isnan(
      `LC_transactions (by {"CustomerID"}-{"CustomerID"})`.`Amount`
    ) THEN null ELSE POW(
      `LC_transactions (by {"CustomerID"}-{"CustomerID"})`.`Amount`, 2
    ) END
  )
  AS `LC_transactions[Amount] (1 week sum of squares)`,
  
  SUM(
    CASE WHEN isnan(
      `LC_transactions (by {"CustomerID"}-{"CustomerID"})`.`Amount`
    ) THEN null ELSE `LC_transactions (by {"CustomerID"}-{"CustomerID"})`.`Amount` END
  )
  AS `LC_transactions[Amount] (1 week sum)`,
  
  MAX(
    CASE WHEN isnan(
      `LC_transactions (by {"CustomerID"}-{"CustomerID"})`.`Amount`
    ) THEN null ELSE `LC_transactions (by {"CustomerID"}-{"CustomerID"})`.`Amount` END
  )
  AS `LC_transactions[Amount] (1 week max)`,
  
  MIN(
    CASE WHEN isnan(
      `LC_transactions (by {"CustomerID"}-{"CustomerID"})`.`Amount`
    ) THEN null ELSE `LC_transactions (by {"CustomerID"}-{"CustomerID"})`.`Amount` END
  )
  AS `LC_transactions[Amount] (1 week min)`,
  
  SUM(
    CAST(
      (
        ISNAN(
          `LC_transactions (by {"CustomerID"}-{"CustomerID"})`.`Amount`
        ) OR ISNULL(
          `LC_transactions (by {"CustomerID"}-{"CustomerID"})`.`Amount`
        )
      ) AS TINYINT
    )
  )
  AS `LC_transactions[Amount] (1 week missing count)`,
  
  dr_agg_to_occurr_map(
    `LC_transactions (by {"CustomerID"}-{"CustomerID"})`.`Description`
  )
  AS `LC_transactions[Description] (1 week value counts)`,
  
  PERCENTILE(
    CASE WHEN isnan(
      `LC_transactions (by {"CustomerID"}-{"CustomerID"})`.`date (days from LC_transactions[Date])`
    ) THEN null ELSE `LC_transactions (by {"CustomerID"}-{"CustomerID"})`.`date (days from LC_transactions[Date])` END, 0.5
  )
  AS `date (days from LC_transactions[Date]) (1 week median)`,
  
  SUM(
    CASE WHEN isnan(
      `LC_transactions (by {"CustomerID"}-{"CustomerID"})`.`date (days from LC_transactions[Date])`
    ) THEN null ELSE POW(
      `LC_transactions (by {"CustomerID"}-{"CustomerID"})`.`date (days from LC_transactions[Date])`, 2
    ) END
  )
  AS `date (days from LC_transactions[Date]) (1 week sum of squares)`,
  
  SUM(
    CASE WHEN isnan(
      `LC_transactions (by {"CustomerID"}-{"CustomerID"})`.`date (days from LC_transactions[Date])`
    ) THEN null ELSE `LC_transactions (by {"CustomerID"}-{"CustomerID"})`.`date (days from LC_transactions[Date])` END
  )
  AS `date (days from LC_transactions[Date]) (1 week sum)`,
  
  MAX(
    CASE WHEN isnan(
      `LC_transactions (by {"CustomerID"}-{"CustomerID"})`.`date (days from LC_transactions[Date])`
    ) THEN null ELSE `LC_transactions (by {"CustomerID"}-{"CustomerID"})`.`date (days from LC_transactions[Date])` END
  )
  AS `date (days from LC_transactions[Date]) (1 week max)`,
  
  MIN(
    CASE WHEN isnan(
      `LC_transactions (by {"CustomerID"}-{"CustomerID"})`.`date (days from LC_transactions[Date])`
    ) THEN null ELSE `LC_transactions (by {"CustomerID"}-{"CustomerID"})`.`date (days from LC_transactions[Date])` END
  )
  AS `date (days from LC_transactions[Date]) (1 week min)`,
  
  SUM(
    CAST(
      (
        ISNAN(
          `LC_transactions (by {"CustomerID"}-{"CustomerID"})`.`date (days from LC_transactions[Date])`
        ) OR ISNULL(
          `LC_transactions (by {"CustomerID"}-{"CustomerID"})`.`date (days from LC_transactions[Date])`
        )
      ) AS TINYINT
    )
  )
  AS `date (days from LC_transactions[Date]) (1 week missing count)`,
  
  PERCENTILE(
    CASE WHEN isnan(
      `LC_transactions (by {"CustomerID"}-{"CustomerID"})`.`LC_transactions (days since previous event by CustomerID)`
    ) THEN null ELSE `LC_transactions (by {"CustomerID"}-{"CustomerID"})`.`LC_transactions (days since previous event by CustomerID)` END, 0.5
  )
  AS `LC_transactions (days since previous event by CustomerID) (1 week median)`,
  
  SUM(
    CASE WHEN isnan(
      `LC_transactions (by {"CustomerID"}-{"CustomerID"})`.`LC_transactions (days since previous event by CustomerID)`
    ) THEN null ELSE POW(
      `LC_transactions (by {"CustomerID"}-{"CustomerID"})`.`LC_transactions (days since previous event by CustomerID)`, 2
    ) END
  )
  AS `LC_transactions (days since previous event by CustomerID) (1 week sum of squares)`,
  
  SUM(
    CASE WHEN isnan(
      `LC_transactions (by {"CustomerID"}-{"CustomerID"})`.`LC_transactions (days since previous event by CustomerID)`
    ) THEN null ELSE `LC_transactions (by {"CustomerID"}-{"CustomerID"})`.`LC_transactions (days since previous event by CustomerID)` END
  )
  AS `LC_transactions (days since previous event by CustomerID) (1 week sum)`,
  
  MAX(
    CASE WHEN isnan(
      `LC_transactions (by {"CustomerID"}-{"CustomerID"})`.`LC_transactions (days since previous event by CustomerID)`
    ) THEN null ELSE `LC_transactions (by {"CustomerID"}-{"CustomerID"})`.`LC_transactions (days since previous event by CustomerID)` END
  )
  AS `LC_transactions (days since previous event by CustomerID) (1 week max)`,
  
  MIN(
    CASE WHEN isnan(
      `LC_transactions (by {"CustomerID"}-{"CustomerID"})`.`LC_transactions (days since previous event by CustomerID)`
    ) THEN null ELSE `LC_transactions (by {"CustomerID"}-{"CustomerID"})`.`LC_transactions (days since previous event by CustomerID)` END
  )
  AS `LC_transactions (days since previous event by CustomerID) (1 week min)`,
  
  SUM(
    CAST(
      (
        ISNAN(
          `LC_transactions (by {"CustomerID"}-{"CustomerID"})`.`LC_transactions (days since previous event by CustomerID)`
        ) OR ISNULL(
          `LC_transactions (by {"CustomerID"}-{"CustomerID"})`.`LC_transactions (days since previous event by CustomerID)`
        )
      ) AS TINYINT
    )
  )
  AS `LC_transactions (days since previous event by CustomerID) (1 week missing count)`,
  
  dr_agg_to_occurr_map(
    `LC_transactions (by {"CustomerID"}-{"CustomerID"})`.`LC_transactions[Date] (Day of Week)`
  )
  AS `LC_transactions[Date] (Day of Week) (1 week value counts)`,
  
  dr_agg_to_occurr_map(
    `LC_transactions (by {"CustomerID"}-{"CustomerID"})`.`LC_transactions[Date] (Day of Month)`
  )
  AS `LC_transactions[Date] (Day of Month) (1 week value counts)`,
  
  dr_agg_to_occurr_map(
    `LC_transactions (by {"CustomerID"}-{"CustomerID"})`.`LC_transactions[Date] (Hour of Day)`
  )
  AS `LC_transactions[Date] (Hour of Day) (1 week value counts)`,
  
  SUM(
    CASE WHEN isnan(
      `LC_transactions (by {"CustomerID"}-{"CustomerID"})`.`LC_transactions[AccountID] (word count)`
    ) THEN null ELSE `LC_transactions (by {"CustomerID"}-{"CustomerID"})`.`LC_transactions[AccountID] (word count)` END
  )
  AS `LC_transactions[AccountID] (word count) (1 week sum)`,
  
  SUM(
    CAST(
      (
        ISNAN(
          `LC_transactions (by {"CustomerID"}-{"CustomerID"})`.`LC_transactions[AccountID] (word count)`
        ) OR ISNULL(
          `LC_transactions (by {"CustomerID"}-{"CustomerID"})`.`LC_transactions[AccountID] (word count)`
        )
      ) AS TINYINT
    )
  )
  AS `LC_transactions[AccountID] (word count) (1 week missing count)`,
  
  dr_agg_merge_map_and_sum_values(
    `LC_transactions (by {"CustomerID"}-{"CustomerID"})`.`LC_transactions[AccountID] (token counts)`
  )
  AS `LC_transactions[AccountID]  (1 week token counts)`,
  
  `LC_transactions (by {"CustomerID"}-{"CustomerID"})`.`CustomerID`,
  
  `LC_transactions (by {"CustomerID"}-{"CustomerID"})`.`SAFER_CUTOFF_598d7e6ae89bde0eadd7456a`

FROM (

  `featurized LC_transactions (by {"CustomerID"}-{"CustomerID"}) (1 week) (view)` AS `LC_transactions (by {"CustomerID"}-{"CustomerID"})`
  
)
GROUP BY

  `CustomerID`, `SAFER_CUTOFF_598d7e6ae89bde0eadd7456a`


/*
BLOCK END -- Create "LC_transactions (aggregated by {"CustomerID"}-{"CustomerID"}) (FDW 1 week)" table with engineered features (1 week)
*/


/* ------------------------------ */

/* -- `featurized LC_transactions (aggregated by {"CustomerID"}-{"CustomerID"}) (FDW 30 days) (30 days) (view)` -- */

CREATE OR REPLACE TEMPORARY VIEW `featurized LC_transactions (aggregated by {"CustomerID"}-{"CustomerID"}) (FDW 30 days) (30 days) (view)` AS 

/*
BLOCK START -- Create "LC_transactions (aggregated by {"CustomerID"}-{"CustomerID"}) (FDW 30 days)" table with engineered features (30 days)

DESCRIPTION:
- Aggregate columns over group keys: `CustomerID`, `SAFER_CUTOFF_598d7e6ae89bde0eadd7456a`
- Apply transformations on columns.
*/

SELECT

  *

FROM (

  SELECT
  
    COUNT(
      *
    )
    AS `LC_transactions (30 days count)`,
    
    PERCENTILE(
      CASE WHEN isnan(
        `LC_transactions (by {"CustomerID"}-{"CustomerID"})`.`Amount`
      ) THEN null ELSE `LC_transactions (by {"CustomerID"}-{"CustomerID"})`.`Amount` END, 0.5
    )
    AS `LC_transactions[Amount] (30 days median)`,
    
    SUM(
      CASE WHEN isnan(
        `LC_transactions (by {"CustomerID"}-{"CustomerID"})`.`Amount`
      ) THEN null ELSE POW(
        `LC_transactions (by {"CustomerID"}-{"CustomerID"})`.`Amount`, 2
      ) END
    )
    AS `LC_transactions[Amount] (30 days sum of squares)`,
    
    SUM(
      CASE WHEN isnan(
        `LC_transactions (by {"CustomerID"}-{"CustomerID"})`.`Amount`
      ) THEN null ELSE `LC_transactions (by {"CustomerID"}-{"CustomerID"})`.`Amount` END
    )
    AS `LC_transactions[Amount] (30 days sum)`,
    
    MAX(
      CASE WHEN isnan(
        `LC_transactions (by {"CustomerID"}-{"CustomerID"})`.`Amount`
      ) THEN null ELSE `LC_transactions (by {"CustomerID"}-{"CustomerID"})`.`Amount` END
    )
    AS `LC_transactions[Amount] (30 days max)`,
    
    MIN(
      CASE WHEN isnan(
        `LC_transactions (by {"CustomerID"}-{"CustomerID"})`.`Amount`
      ) THEN null ELSE `LC_transactions (by {"CustomerID"}-{"CustomerID"})`.`Amount` END
    )
    AS `LC_transactions[Amount] (30 days min)`,
    
    SUM(
      CAST(
        (
          ISNAN(
            `LC_transactions (by {"CustomerID"}-{"CustomerID"})`.`Amount`
          ) OR ISNULL(
            `LC_transactions (by {"CustomerID"}-{"CustomerID"})`.`Amount`
          )
        ) AS TINYINT
      )
    )
    AS `LC_transactions[Amount] (30 days missing count)`,
    
    dr_agg_to_occurr_map(
      `LC_transactions (by {"CustomerID"}-{"CustomerID"})`.`Description`
    )
    AS `LC_transactions[Description] (30 days value counts)`,
    
    PERCENTILE(
      CASE WHEN isnan(
        `LC_transactions (by {"CustomerID"}-{"CustomerID"})`.`date (days from LC_transactions[Date])`
      ) THEN null ELSE `LC_transactions (by {"CustomerID"}-{"CustomerID"})`.`date (days from LC_transactions[Date])` END, 0.5
    )
    AS `date (days from LC_transactions[Date]) (30 days median)`,
    
    SUM(
      CASE WHEN isnan(
        `LC_transactions (by {"CustomerID"}-{"CustomerID"})`.`date (days from LC_transactions[Date])`
      ) THEN null ELSE POW(
        `LC_transactions (by {"CustomerID"}-{"CustomerID"})`.`date (days from LC_transactions[Date])`, 2
      ) END
    )
    AS `date (days from LC_transactions[Date]) (30 days sum of squares)`,
    
    SUM(
      CASE WHEN isnan(
        `LC_transactions (by {"CustomerID"}-{"CustomerID"})`.`date (days from LC_transactions[Date])`
      ) THEN null ELSE `LC_transactions (by {"CustomerID"}-{"CustomerID"})`.`date (days from LC_transactions[Date])` END
    )
    AS `date (days from LC_transactions[Date]) (30 days sum)`,
    
    MAX(
      CASE WHEN isnan(
        `LC_transactions (by {"CustomerID"}-{"CustomerID"})`.`date (days from LC_transactions[Date])`
      ) THEN null ELSE `LC_transactions (by {"CustomerID"}-{"CustomerID"})`.`date (days from LC_transactions[Date])` END
    )
    AS `date (days from LC_transactions[Date]) (30 days max)`,
    
    SUM(
      CAST(
        (
          ISNAN(
            `LC_transactions (by {"CustomerID"}-{"CustomerID"})`.`date (days from LC_transactions[Date])`
          ) OR ISNULL(
            `LC_transactions (by {"CustomerID"}-{"CustomerID"})`.`date (days from LC_transactions[Date])`
          )
        ) AS TINYINT
      )
    )
    AS `date (days from LC_transactions[Date]) (30 days missing count)`,
    
    PERCENTILE(
      CASE WHEN isnan(
        `LC_transactions (by {"CustomerID"}-{"CustomerID"})`.`LC_transactions (days since previous event by CustomerID)`
      ) THEN null ELSE `LC_transactions (by {"CustomerID"}-{"CustomerID"})`.`LC_transactions (days since previous event by CustomerID)` END, 0.5
    )
    AS `LC_transactions (days since previous event by CustomerID) (30 days median)`,
    
    SUM(
      CASE WHEN isnan(
        `LC_transactions (by {"CustomerID"}-{"CustomerID"})`.`LC_transactions (days since previous event by CustomerID)`
      ) THEN null ELSE POW(
        `LC_transactions (by {"CustomerID"}-{"CustomerID"})`.`LC_transactions (days since previous event by CustomerID)`, 2
      ) END
    )
    AS `LC_transactions (days since previous event by CustomerID) (30 days sum of squares)`,
    
    SUM(
      CASE WHEN isnan(
        `LC_transactions (by {"CustomerID"}-{"CustomerID"})`.`LC_transactions (days since previous event by CustomerID)`
      ) THEN null ELSE `LC_transactions (by {"CustomerID"}-{"CustomerID"})`.`LC_transactions (days since previous event by CustomerID)` END
    )
    AS `LC_transactions (days since previous event by CustomerID) (30 days sum)`,
    
    MAX(
      CASE WHEN isnan(
        `LC_transactions (by {"CustomerID"}-{"CustomerID"})`.`LC_transactions (days since previous event by CustomerID)`
      ) THEN null ELSE `LC_transactions (by {"CustomerID"}-{"CustomerID"})`.`LC_transactions (days since previous event by CustomerID)` END
    )
    AS `LC_transactions (days since previous event by CustomerID) (30 days max)`,
    
    MIN(
      CASE WHEN isnan(
        `LC_transactions (by {"CustomerID"}-{"CustomerID"})`.`LC_transactions (days since previous event by CustomerID)`
      ) THEN null ELSE `LC_transactions (by {"CustomerID"}-{"CustomerID"})`.`LC_transactions (days since previous event by CustomerID)` END
    )
    AS `LC_transactions (days since previous event by CustomerID) (30 days min)`,
    
    SUM(
      CAST(
        (
          ISNAN(
            `LC_transactions (by {"CustomerID"}-{"CustomerID"})`.`LC_transactions (days since previous event by CustomerID)`
          ) OR ISNULL(
            `LC_transactions (by {"CustomerID"}-{"CustomerID"})`.`LC_transactions (days since previous event by CustomerID)`
          )
        ) AS TINYINT
      )
    )
    AS `LC_transactions (days since previous event by CustomerID) (30 days missing count)`,
    
    dr_agg_to_occurr_map(
      `LC_transactions (by {"CustomerID"}-{"CustomerID"})`.`LC_transactions[Date] (Day of Week)`
    )
    AS `LC_transactions[Date] (Day of Week) (30 days value counts)`,
    
    dr_agg_to_occurr_map(
      `LC_transactions (by {"CustomerID"}-{"CustomerID"})`.`LC_transactions[Date] (Day of Month)`
    )
    AS `LC_transactions[Date] (Day of Month) (30 days value counts)`,
    
    dr_agg_to_occurr_map(
      `LC_transactions (by {"CustomerID"}-{"CustomerID"})`.`LC_transactions[Date] (Hour of Day)`
    )
    AS `LC_transactions[Date] (Hour of Day) (30 days value counts)`,
    
    SUM(
      CASE WHEN isnan(
        `LC_transactions (by {"CustomerID"}-{"CustomerID"})`.`LC_transactions[AccountID] (word count)`
      ) THEN null ELSE `LC_transactions (by {"CustomerID"}-{"CustomerID"})`.`LC_transactions[AccountID] (word count)` END
    )
    AS `LC_transactions[AccountID] (word count) (30 days sum)`,
    
    SUM(
      CAST(
        (
          ISNAN(
            `LC_transactions (by {"CustomerID"}-{"CustomerID"})`.`LC_transactions[AccountID] (word count)`
          ) OR ISNULL(
            `LC_transactions (by {"CustomerID"}-{"CustomerID"})`.`LC_transactions[AccountID] (word count)`
          )
        ) AS TINYINT
      )
    )
    AS `LC_transactions[AccountID] (word count) (30 days missing count)`,
    
    dr_agg_merge_map_and_sum_values(
      `LC_transactions (by {"CustomerID"}-{"CustomerID"})`.`LC_transactions[AccountID] (token counts)`
    )
    AS `LC_transactions[AccountID]  (30 days token counts)`,
    
    `LC_transactions (by {"CustomerID"}-{"CustomerID"})`.`CustomerID`,
    
    `LC_transactions (by {"CustomerID"}-{"CustomerID"})`.`SAFER_CUTOFF_598d7e6ae89bde0eadd7456a`
  
  FROM (
  
    `featurized LC_transactions (by {"CustomerID"}-{"CustomerID"}) (30 days) (view)` AS `LC_transactions (by {"CustomerID"}-{"CustomerID"})`
    
  )
  GROUP BY
  
    `CustomerID`, `SAFER_CUTOFF_598d7e6ae89bde0eadd7456a`
  
  
)
LEFT JOIN (

  SELECT
  
    *
  
  FROM (
  
    SELECT
    
      `LC_transactions (by {"CustomerID"}-{"CustomerID"})`.`AccountID`
      AS `LC_transactions[AccountID] (30 days latest)`,
      
      `LC_transactions (by {"CustomerID"}-{"CustomerID"})`.`Amount`
      AS `LC_transactions[Amount] (30 days latest)`,
      
      `LC_transactions (by {"CustomerID"}-{"CustomerID"})`.`Description`
      AS `LC_transactions[Description] (30 days latest)`,
      
      `LC_transactions (by {"CustomerID"}-{"CustomerID"})`.`date (days from LC_transactions[Date])`
      AS `date (days from LC_transactions[Date]) (30 days latest)`,
      
      `LC_transactions (by {"CustomerID"}-{"CustomerID"})`.`LC_transactions[Date] (Day of Week)`
      AS `LC_transactions[Date] (Day of Week) (30 days latest)`,
      
      `LC_transactions (by {"CustomerID"}-{"CustomerID"})`.`LC_transactions[Date] (Day of Month)`
      AS `LC_transactions[Date] (Day of Month) (30 days latest)`,
      
      `LC_transactions (by {"CustomerID"}-{"CustomerID"})`.`CustomerID` AS __key_prefix_0,
      
      `LC_transactions (by {"CustomerID"}-{"CustomerID"})`.`SAFER_CUTOFF_598d7e6ae89bde0eadd7456a` AS __key_prefix_1,
      
      lead(
        SAFER_ROW_ID_598d7e6ae89bde0eadd7456c, 1
      ) OVER asc_order
      AS `SAFER_RANK_598d7e6ae89bde0eadd74568`
    
    FROM (
    
      `featurized LC_transactions (by {"CustomerID"}-{"CustomerID"}) (30 days) (view)` AS `LC_transactions (by {"CustomerID"}-{"CustomerID"})`
      
    )
    
    WINDOW
    
      `asc_order` AS (PARTITION BY `CustomerID`, `SAFER_CUTOFF_598d7e6ae89bde0eadd7456a` ORDER BY `Date` ASC, `SAFER_ROW_HASH_598d7e6ae89bde0eadd7456d` ASC, `SAFER_ROW_ID_598d7e6ae89bde0eadd7456c` ASC)
    
  )
  
  WHERE
  
    `SAFER_RANK_598d7e6ae89bde0eadd74568` IS NULL
  
) AS `LC_transactions (by {"CustomerID"}-{"CustomerID"})`

ON

  `CustomerID` = `LC_transactions (by {"CustomerID"}-{"CustomerID"})`.`__key_prefix_0` AND
  `SAFER_CUTOFF_598d7e6ae89bde0eadd7456a` = `LC_transactions (by {"CustomerID"}-{"CustomerID"})`.`__key_prefix_1`

/*
BLOCK END -- Create "LC_transactions (aggregated by {"CustomerID"}-{"CustomerID"}) (FDW 30 days)" table with engineered features (30 days)
*/


/* ------------------------------ */

/*
BLOCK START -- Create "DR_PRIMARY_TABLE" table with engineered features

DESCRIPTION:
- Left join "LC_transactions (aggregated by {"CustomerID"}-{"CustomerID"}) (FDW 1 week)" table (1 week) to "DR_PRIMARY_TABLE" table.
- Left join "LC_transactions (aggregated by {"CustomerID"}-{"CustomerID"}) (FDW 30 days)" table (30 days) to "DR_PRIMARY_TABLE" table.
- Apply transformations on columns.
*/

SELECT

  dr_numeric_rounding(
    `LC_transactions (aggregated by {"CustomerID"}-{"CustomerID"}) (FDW 30 days)`.`LC_transactions (days since previous event by CustomerID) (30 days max)`
  )
  AS `LC_transactions (days since previous event by CustomerID) (30 days max)`,
  
  dr_get_max_value_key(
    `LC_transactions (aggregated by {"CustomerID"}-{"CustomerID"}) (FDW 1 week)`.`LC_transactions[Date] (Day of Week) (1 week value counts)`
  )
  AS `LC_transactions[Date] (Day of Week) (1 week most frequent)`,
  
  `LC_transactions (aggregated by {"CustomerID"}-{"CustomerID"}) (FDW 30 days)`.`LC_transactions[Date] (Day of Week) (30 days latest)`,
  
  dr_numeric_rounding(
    `LC_transactions (aggregated by {"CustomerID"}-{"CustomerID"}) (FDW 30 days)`.`LC_transactions (days since previous event by CustomerID) (30 days sum)` / (
      coalesce(
        `LC_transactions (aggregated by {"CustomerID"}-{"CustomerID"}) (FDW 30 days)`.`LC_transactions (30 days count)`, 0
      ) - `LC_transactions (aggregated by {"CustomerID"}-{"CustomerID"}) (FDW 30 days)`.`LC_transactions (days since previous event by CustomerID) (30 days missing count)`
    )
  )
  AS `LC_transactions (days since previous event by CustomerID) (30 days avg)`,
  
  `DR_PRIMARY_TABLE`.`BadLoan`,
  
  dr_numeric_rounding(
    CASE     WHEN `LC_transactions (aggregated by {"CustomerID"}-{"CustomerID"}) (FDW 30 days)`.`LC_transactions[Amount] (30 days sum of squares)` / (
      coalesce(
        `LC_transactions (aggregated by {"CustomerID"}-{"CustomerID"}) (FDW 30 days)`.`LC_transactions (30 days count)`, 0
      ) - `LC_transactions (aggregated by {"CustomerID"}-{"CustomerID"}) (FDW 30 days)`.`LC_transactions[Amount] (30 days missing count)`
    ) < 1e-11 THEN 0     WHEN POW(
      `LC_transactions (aggregated by {"CustomerID"}-{"CustomerID"}) (FDW 30 days)`.`LC_transactions[Amount] (30 days sum)` / (
        coalesce(
          `LC_transactions (aggregated by {"CustomerID"}-{"CustomerID"}) (FDW 30 days)`.`LC_transactions (30 days count)`, 0
        ) - `LC_transactions (aggregated by {"CustomerID"}-{"CustomerID"}) (FDW 30 days)`.`LC_transactions[Amount] (30 days missing count)`
      ), 2
    ) < 1e-11 OR        (
      (
        `LC_transactions (aggregated by {"CustomerID"}-{"CustomerID"}) (FDW 30 days)`.`LC_transactions[Amount] (30 days sum of squares)` / (
          coalesce(
            `LC_transactions (aggregated by {"CustomerID"}-{"CustomerID"}) (FDW 30 days)`.`LC_transactions (30 days count)`, 0
          ) - `LC_transactions (aggregated by {"CustomerID"}-{"CustomerID"}) (FDW 30 days)`.`LC_transactions[Amount] (30 days missing count)`
        )
      ) / (
        POW(
          `LC_transactions (aggregated by {"CustomerID"}-{"CustomerID"}) (FDW 30 days)`.`LC_transactions[Amount] (30 days sum)` / (
            coalesce(
              `LC_transactions (aggregated by {"CustomerID"}-{"CustomerID"}) (FDW 30 days)`.`LC_transactions (30 days count)`, 0
            ) - `LC_transactions (aggregated by {"CustomerID"}-{"CustomerID"}) (FDW 30 days)`.`LC_transactions[Amount] (30 days missing count)`
          ), 2
        )
      )
    ) > 1.00000000001        THEN SQRT(
      `LC_transactions (aggregated by {"CustomerID"}-{"CustomerID"}) (FDW 30 days)`.`LC_transactions[Amount] (30 days sum of squares)` / (
        coalesce(
          `LC_transactions (aggregated by {"CustomerID"}-{"CustomerID"}) (FDW 30 days)`.`LC_transactions (30 days count)`, 0
        ) - `LC_transactions (aggregated by {"CustomerID"}-{"CustomerID"}) (FDW 30 days)`.`LC_transactions[Amount] (30 days missing count)`
      ) - POW(
        `LC_transactions (aggregated by {"CustomerID"}-{"CustomerID"}) (FDW 30 days)`.`LC_transactions[Amount] (30 days sum)` / (
          coalesce(
            `LC_transactions (aggregated by {"CustomerID"}-{"CustomerID"}) (FDW 30 days)`.`LC_transactions (30 days count)`, 0
          ) - `LC_transactions (aggregated by {"CustomerID"}-{"CustomerID"}) (FDW 30 days)`.`LC_transactions[Amount] (30 days missing count)`
        ), 2
      )
    )     ELSE 0 END
  )
  AS `LC_transactions[Amount] (30 days std)`,
  
  dr_numeric_rounding(
    `LC_transactions (aggregated by {"CustomerID"}-{"CustomerID"}) (FDW 1 week)`.`LC_transactions[Amount] (1 week min)`
  )
  AS `LC_transactions[Amount] (1 week min)`,
  
  dr_numeric_rounding(
    coalesce(
      size(
        `LC_transactions (aggregated by {"CustomerID"}-{"CustomerID"}) (FDW 30 days)`.`LC_transactions[Description] (30 days value counts)`
      ), 0
    )
  )
  AS `LC_transactions[Description] (30 days unique count)`,
  
  `LC_transactions (aggregated by {"CustomerID"}-{"CustomerID"}) (FDW 30 days)`.`LC_transactions[Date] (Day of Month) (30 days latest)`,
  
  dr_numeric_rounding(
    `LC_transactions (aggregated by {"CustomerID"}-{"CustomerID"}) (FDW 30 days)`.`LC_transactions[Amount] (30 days min)`
  )
  AS `LC_transactions[Amount] (30 days min)`,
  
  dr_numeric_rounding(
    `LC_transactions (aggregated by {"CustomerID"}-{"CustomerID"}) (FDW 30 days)`.`date (days from LC_transactions[Date]) (30 days max)`
  )
  AS `date (days from LC_transactions[Date]) (30 days max)`,
  
  `DR_PRIMARY_TABLE`.`LC_profile[term]`,
  
  coalesce(
    `LC_transactions (aggregated by {"CustomerID"}-{"CustomerID"}) (FDW 30 days)`.`LC_transactions (30 days count)`, 0
  )
  AS `LC_transactions (30 days count)`,
  
  dr_numeric_rounding(
    `LC_transactions (aggregated by {"CustomerID"}-{"CustomerID"}) (FDW 1 week)`.`date (days from LC_transactions[Date]) (1 week max)`
  )
  AS `date (days from LC_transactions[Date]) (1 week max)`,
  
  dr_numeric_rounding(
    `LC_transactions (aggregated by {"CustomerID"}-{"CustomerID"}) (FDW 30 days)`.`date (days from LC_transactions[Date]) (30 days median)`
  )
  AS `date (days from LC_transactions[Date]) (30 days median)`,
  
  `LC_transactions (aggregated by {"CustomerID"}-{"CustomerID"}) (FDW 30 days)`.`LC_transactions[AccountID] (word count) (30 days missing count)`,
  
  dr_numeric_rounding(
    `LC_transactions (aggregated by {"CustomerID"}-{"CustomerID"}) (FDW 1 week)`.`date (days from LC_transactions[Date]) (1 week sum)` / (
      coalesce(
        `LC_transactions (aggregated by {"CustomerID"}-{"CustomerID"}) (FDW 1 week)`.`LC_transactions (1 week count)`, 0
      ) - `LC_transactions (aggregated by {"CustomerID"}-{"CustomerID"}) (FDW 1 week)`.`date (days from LC_transactions[Date]) (1 week missing count)`
    )
  )
  AS `date (days from LC_transactions[Date]) (1 week avg)`,
  
  dr_numeric_rounding(
    coalesce(
      element_at(
        `LC_transactions (aggregated by {"CustomerID"}-{"CustomerID"}) (FDW 30 days)`.`LC_transactions[Description] (30 days value counts)`, '==Missing=='
      ), 0
    )
  )
  AS `LC_transactions[Description] (30 days missing count)`,
  
  dr_get_max_value_key(
    `LC_transactions (aggregated by {"CustomerID"}-{"CustomerID"}) (FDW 30 days)`.`LC_transactions[Date] (Day of Month) (30 days value counts)`
  )
  AS `LC_transactions[Date] (Day of Month) (30 days most frequent)`,
  
  dr_numeric_rounding(
    `DR_PRIMARY_TABLE`.`LC_profile[emp_title] (word count)`
  )
  AS `LC_profile[emp_title] (word count)`,
  
  dr_numeric_rounding(
    `LC_transactions (aggregated by {"CustomerID"}-{"CustomerID"}) (FDW 30 days)`.`LC_transactions[Amount] (30 days sum)`
  )
  AS `LC_transactions[Amount] (30 days sum)`,
  
  dr_map_to_json(
    `LC_transactions (aggregated by {"CustomerID"}-{"CustomerID"}) (FDW 30 days)`.`LC_transactions[AccountID]  (30 days token counts)`
  )
  AS `LC_transactions[AccountID] (30 days tokens)`,
  
  `DR_PRIMARY_TABLE`.`LC_profile[verification_status]`,
  
  `DR_PRIMARY_TABLE`.`LC_profile[home_ownership]`,
  
  dr_numeric_rounding(
    dr_entropy_from_map(
      `LC_transactions (aggregated by {"CustomerID"}-{"CustomerID"}) (FDW 30 days)`.`LC_transactions[Date] (Day of Month) (30 days value counts)`
    )
  )
  AS `LC_transactions[Date] (Day of Month) (30 days entropy)`,
  
  `LC_transactions (aggregated by {"CustomerID"}-{"CustomerID"}) (FDW 30 days)`.`LC_transactions[Amount] (30 days missing count)`,
  
  dr_map_to_json(
    `LC_transactions (aggregated by {"CustomerID"}-{"CustomerID"}) (FDW 1 week)`.`LC_transactions[Date] (Day of Week) (1 week value counts)`
  )
  AS `LC_transactions[Date] (Day of Week) (1 week counts)`,
  
  dr_get_max_value_key(
    `LC_transactions (aggregated by {"CustomerID"}-{"CustomerID"}) (FDW 1 week)`.`LC_transactions[Description] (1 week value counts)`
  )
  AS `LC_transactions[Description] (1 week most frequent)`,
  
  dr_numeric_rounding(
    `LC_transactions (aggregated by {"CustomerID"}-{"CustomerID"}) (FDW 30 days)`.`LC_transactions[Amount] (30 days sum)` / (
      coalesce(
        `LC_transactions (aggregated by {"CustomerID"}-{"CustomerID"}) (FDW 30 days)`.`LC_transactions (30 days count)`, 0
      ) - `LC_transactions (aggregated by {"CustomerID"}-{"CustomerID"}) (FDW 30 days)`.`LC_transactions[Amount] (30 days missing count)`
    )
  )
  AS `LC_transactions[Amount] (30 days avg)`,
  
  `LC_transactions (aggregated by {"CustomerID"}-{"CustomerID"}) (FDW 1 week)`.`LC_transactions[AccountID] (word count) (1 week missing count)`,
  
  dr_numeric_rounding(
    `LC_transactions (aggregated by {"CustomerID"}-{"CustomerID"}) (FDW 1 week)`.`LC_transactions (days since previous event by CustomerID) (1 week sum)` / (
      coalesce(
        `LC_transactions (aggregated by {"CustomerID"}-{"CustomerID"}) (FDW 1 week)`.`LC_transactions (1 week count)`, 0
      ) - `LC_transactions (aggregated by {"CustomerID"}-{"CustomerID"}) (FDW 1 week)`.`LC_transactions (days since previous event by CustomerID) (1 week missing count)`
    )
  )
  AS `LC_transactions (days since previous event by CustomerID) (1 week avg)`,
  
  dr_numeric_rounding(
    `LC_transactions (aggregated by {"CustomerID"}-{"CustomerID"}) (FDW 1 week)`.`LC_transactions (days since previous event by CustomerID) (1 week min)`
  )
  AS `LC_transactions (days since previous event by CustomerID) (1 week min)`,
  
  coalesce(
    `LC_transactions (aggregated by {"CustomerID"}-{"CustomerID"}) (FDW 1 week)`.`LC_transactions (1 week count)`, 0
  )
  AS `LC_transactions (1 week count)`,
  
  dr_numeric_rounding(
    CASE     WHEN `LC_transactions (aggregated by {"CustomerID"}-{"CustomerID"}) (FDW 1 week)`.`LC_transactions[Amount] (1 week sum of squares)` / (
      coalesce(
        `LC_transactions (aggregated by {"CustomerID"}-{"CustomerID"}) (FDW 1 week)`.`LC_transactions (1 week count)`, 0
      ) - `LC_transactions (aggregated by {"CustomerID"}-{"CustomerID"}) (FDW 1 week)`.`LC_transactions[Amount] (1 week missing count)`
    ) < 1e-11 THEN 0     WHEN POW(
      `LC_transactions (aggregated by {"CustomerID"}-{"CustomerID"}) (FDW 1 week)`.`LC_transactions[Amount] (1 week sum)` / (
        coalesce(
          `LC_transactions (aggregated by {"CustomerID"}-{"CustomerID"}) (FDW 1 week)`.`LC_transactions (1 week count)`, 0
        ) - `LC_transactions (aggregated by {"CustomerID"}-{"CustomerID"}) (FDW 1 week)`.`LC_transactions[Amount] (1 week missing count)`
      ), 2
    ) < 1e-11 OR        (
      (
        `LC_transactions (aggregated by {"CustomerID"}-{"CustomerID"}) (FDW 1 week)`.`LC_transactions[Amount] (1 week sum of squares)` / (
          coalesce(
            `LC_transactions (aggregated by {"CustomerID"}-{"CustomerID"}) (FDW 1 week)`.`LC_transactions (1 week count)`, 0
          ) - `LC_transactions (aggregated by {"CustomerID"}-{"CustomerID"}) (FDW 1 week)`.`LC_transactions[Amount] (1 week missing count)`
        )
      ) / (
        POW(
          `LC_transactions (aggregated by {"CustomerID"}-{"CustomerID"}) (FDW 1 week)`.`LC_transactions[Amount] (1 week sum)` / (
            coalesce(
              `LC_transactions (aggregated by {"CustomerID"}-{"CustomerID"}) (FDW 1 week)`.`LC_transactions (1 week count)`, 0
            ) - `LC_transactions (aggregated by {"CustomerID"}-{"CustomerID"}) (FDW 1 week)`.`LC_transactions[Amount] (1 week missing count)`
          ), 2
        )
      )
    ) > 1.00000000001        THEN SQRT(
      `LC_transactions (aggregated by {"CustomerID"}-{"CustomerID"}) (FDW 1 week)`.`LC_transactions[Amount] (1 week sum of squares)` / (
        coalesce(
          `LC_transactions (aggregated by {"CustomerID"}-{"CustomerID"}) (FDW 1 week)`.`LC_transactions (1 week count)`, 0
        ) - `LC_transactions (aggregated by {"CustomerID"}-{"CustomerID"}) (FDW 1 week)`.`LC_transactions[Amount] (1 week missing count)`
      ) - POW(
        `LC_transactions (aggregated by {"CustomerID"}-{"CustomerID"}) (FDW 1 week)`.`LC_transactions[Amount] (1 week sum)` / (
          coalesce(
            `LC_transactions (aggregated by {"CustomerID"}-{"CustomerID"}) (FDW 1 week)`.`LC_transactions (1 week count)`, 0
          ) - `LC_transactions (aggregated by {"CustomerID"}-{"CustomerID"}) (FDW 1 week)`.`LC_transactions[Amount] (1 week missing count)`
        ), 2
      )
    )     ELSE 0 END
  )
  AS `LC_transactions[Amount] (1 week std)`,
  
  `DR_PRIMARY_TABLE`.`LC_profile[purpose]`,
  
  `LC_transactions (aggregated by {"CustomerID"}-{"CustomerID"}) (FDW 1 week)`.`LC_transactions[Amount] (1 week missing count)`,
  
  dr_map_to_json(
    `LC_transactions (aggregated by {"CustomerID"}-{"CustomerID"}) (FDW 30 days)`.`LC_transactions[Date] (Day of Month) (30 days value counts)`
  )
  AS `LC_transactions[Date] (Day of Month) (30 days counts)`,
  
  dr_numeric_rounding(
    CASE     WHEN `LC_transactions (aggregated by {"CustomerID"}-{"CustomerID"}) (FDW 1 week)`.`LC_transactions (days since previous event by CustomerID) (1 week sum of squares)` / (
      coalesce(
        `LC_transactions (aggregated by {"CustomerID"}-{"CustomerID"}) (FDW 1 week)`.`LC_transactions (1 week count)`, 0
      ) - `LC_transactions (aggregated by {"CustomerID"}-{"CustomerID"}) (FDW 1 week)`.`LC_transactions (days since previous event by CustomerID) (1 week missing count)`
    ) < 1e-11 THEN 0     WHEN POW(
      `LC_transactions (aggregated by {"CustomerID"}-{"CustomerID"}) (FDW 1 week)`.`LC_transactions (days since previous event by CustomerID) (1 week sum)` / (
        coalesce(
          `LC_transactions (aggregated by {"CustomerID"}-{"CustomerID"}) (FDW 1 week)`.`LC_transactions (1 week count)`, 0
        ) - `LC_transactions (aggregated by {"CustomerID"}-{"CustomerID"}) (FDW 1 week)`.`LC_transactions (days since previous event by CustomerID) (1 week missing count)`
      ), 2
    ) < 1e-11 OR        (
      (
        `LC_transactions (aggregated by {"CustomerID"}-{"CustomerID"}) (FDW 1 week)`.`LC_transactions (days since previous event by CustomerID) (1 week sum of squares)` / (
          coalesce(
            `LC_transactions (aggregated by {"CustomerID"}-{"CustomerID"}) (FDW 1 week)`.`LC_transactions (1 week count)`, 0
          ) - `LC_transactions (aggregated by {"CustomerID"}-{"CustomerID"}) (FDW 1 week)`.`LC_transactions (days since previous event by CustomerID) (1 week missing count)`
        )
      ) / (
        POW(
          `LC_transactions (aggregated by {"CustomerID"}-{"CustomerID"}) (FDW 1 week)`.`LC_transactions (days since previous event by CustomerID) (1 week sum)` / (
            coalesce(
              `LC_transactions (aggregated by {"CustomerID"}-{"CustomerID"}) (FDW 1 week)`.`LC_transactions (1 week count)`, 0
            ) - `LC_transactions (aggregated by {"CustomerID"}-{"CustomerID"}) (FDW 1 week)`.`LC_transactions (days since previous event by CustomerID) (1 week missing count)`
          ), 2
        )
      )
    ) > 1.00000000001        THEN SQRT(
      `LC_transactions (aggregated by {"CustomerID"}-{"CustomerID"}) (FDW 1 week)`.`LC_transactions (days since previous event by CustomerID) (1 week sum of squares)` / (
        coalesce(
          `LC_transactions (aggregated by {"CustomerID"}-{"CustomerID"}) (FDW 1 week)`.`LC_transactions (1 week count)`, 0
        ) - `LC_transactions (aggregated by {"CustomerID"}-{"CustomerID"}) (FDW 1 week)`.`LC_transactions (days since previous event by CustomerID) (1 week missing count)`
      ) - POW(
        `LC_transactions (aggregated by {"CustomerID"}-{"CustomerID"}) (FDW 1 week)`.`LC_transactions (days since previous event by CustomerID) (1 week sum)` / (
          coalesce(
            `LC_transactions (aggregated by {"CustomerID"}-{"CustomerID"}) (FDW 1 week)`.`LC_transactions (1 week count)`, 0
          ) - `LC_transactions (aggregated by {"CustomerID"}-{"CustomerID"}) (FDW 1 week)`.`LC_transactions (days since previous event by CustomerID) (1 week missing count)`
        ), 2
      )
    )     ELSE 0 END
  )
  AS `LC_transactions (days since previous event by CustomerID) (1 week std)`,
  
  dr_numeric_rounding(
    `DR_PRIMARY_TABLE`.`LC_profile[annual_inc]`
  )
  AS `LC_profile[annual_inc]`,
  
  `DR_PRIMARY_TABLE`.`LC_profile[loan_amnt]`,
  
  dr_numeric_rounding(
    coalesce(
      size(
        `LC_transactions (aggregated by {"CustomerID"}-{"CustomerID"}) (FDW 30 days)`.`LC_transactions[Date] (Day of Month) (30 days value counts)`
      ), 0
    )
  )
  AS `LC_transactions[Date] (Day of Month) (30 days unique count)`,
  
  dr_numeric_rounding(
    `LC_transactions (aggregated by {"CustomerID"}-{"CustomerID"}) (FDW 1 week)`.`LC_transactions (days since previous event by CustomerID) (1 week max)`
  )
  AS `LC_transactions (days since previous event by CustomerID) (1 week max)`,
  
  dr_get_max_value_key(
    `LC_transactions (aggregated by {"CustomerID"}-{"CustomerID"}) (FDW 30 days)`.`LC_transactions[Description] (30 days value counts)`
  )
  AS `LC_transactions[Description] (30 days most frequent)`,
  
  dr_map_to_json(
    `LC_transactions (aggregated by {"CustomerID"}-{"CustomerID"}) (FDW 30 days)`.`LC_transactions[Date] (Day of Week) (30 days value counts)`
  )
  AS `LC_transactions[Date] (Day of Week) (30 days counts)`,
  
  dr_numeric_rounding(
    coalesce(
      size(
        `LC_transactions (aggregated by {"CustomerID"}-{"CustomerID"}) (FDW 30 days)`.`LC_transactions[Date] (Hour of Day) (30 days value counts)`
      ), 0
    )
  )
  AS `LC_transactions[Date] (Hour of Day) (30 days unique count)`,
  
  `LC_transactions (aggregated by {"CustomerID"}-{"CustomerID"}) (FDW 1 week)`.`LC_transactions (days since previous event by CustomerID) (1 week missing count)`,
  
  dr_numeric_rounding(
    `LC_transactions (aggregated by {"CustomerID"}-{"CustomerID"}) (FDW 1 week)`.`LC_transactions (days since previous event by CustomerID) (1 week sum)`
  )
  AS `LC_transactions (days since previous event by CustomerID) (1 week sum)`,
  
  dr_numeric_rounding(
    `LC_transactions (aggregated by {"CustomerID"}-{"CustomerID"}) (FDW 30 days)`.`LC_transactions[Amount] (30 days latest)`
  )
  AS `LC_transactions[Amount] (30 days latest)`,
  
  dr_numeric_rounding(
    `LC_transactions (aggregated by {"CustomerID"}-{"CustomerID"}) (FDW 1 week)`.`date (days from LC_transactions[Date]) (1 week sum)`
  )
  AS `date (days from LC_transactions[Date]) (1 week sum)`,
  
  dr_numeric_rounding(
    coalesce(
      size(
        `LC_transactions (aggregated by {"CustomerID"}-{"CustomerID"}) (FDW 1 week)`.`LC_transactions[Date] (Day of Month) (1 week value counts)`
      ), 0
    )
  )
  AS `LC_transactions[Date] (Day of Month) (1 week unique count)`,
  
  dr_numeric_rounding(
    CASE     WHEN `LC_transactions (aggregated by {"CustomerID"}-{"CustomerID"}) (FDW 30 days)`.`LC_transactions (days since previous event by CustomerID) (30 days sum of squares)` / (
      coalesce(
        `LC_transactions (aggregated by {"CustomerID"}-{"CustomerID"}) (FDW 30 days)`.`LC_transactions (30 days count)`, 0
      ) - `LC_transactions (aggregated by {"CustomerID"}-{"CustomerID"}) (FDW 30 days)`.`LC_transactions (days since previous event by CustomerID) (30 days missing count)`
    ) < 1e-11 THEN 0     WHEN POW(
      `LC_transactions (aggregated by {"CustomerID"}-{"CustomerID"}) (FDW 30 days)`.`LC_transactions (days since previous event by CustomerID) (30 days sum)` / (
        coalesce(
          `LC_transactions (aggregated by {"CustomerID"}-{"CustomerID"}) (FDW 30 days)`.`LC_transactions (30 days count)`, 0
        ) - `LC_transactions (aggregated by {"CustomerID"}-{"CustomerID"}) (FDW 30 days)`.`LC_transactions (days since previous event by CustomerID) (30 days missing count)`
      ), 2
    ) < 1e-11 OR        (
      (
        `LC_transactions (aggregated by {"CustomerID"}-{"CustomerID"}) (FDW 30 days)`.`LC_transactions (days since previous event by CustomerID) (30 days sum of squares)` / (
          coalesce(
            `LC_transactions (aggregated by {"CustomerID"}-{"CustomerID"}) (FDW 30 days)`.`LC_transactions (30 days count)`, 0
          ) - `LC_transactions (aggregated by {"CustomerID"}-{"CustomerID"}) (FDW 30 days)`.`LC_transactions (days since previous event by CustomerID) (30 days missing count)`
        )
      ) / (
        POW(
          `LC_transactions (aggregated by {"CustomerID"}-{"CustomerID"}) (FDW 30 days)`.`LC_transactions (days since previous event by CustomerID) (30 days sum)` / (
            coalesce(
              `LC_transactions (aggregated by {"CustomerID"}-{"CustomerID"}) (FDW 30 days)`.`LC_transactions (30 days count)`, 0
            ) - `LC_transactions (aggregated by {"CustomerID"}-{"CustomerID"}) (FDW 30 days)`.`LC_transactions (days since previous event by CustomerID) (30 days missing count)`
          ), 2
        )
      )
    ) > 1.00000000001        THEN SQRT(
      `LC_transactions (aggregated by {"CustomerID"}-{"CustomerID"}) (FDW 30 days)`.`LC_transactions (days since previous event by CustomerID) (30 days sum of squares)` / (
        coalesce(
          `LC_transactions (aggregated by {"CustomerID"}-{"CustomerID"}) (FDW 30 days)`.`LC_transactions (30 days count)`, 0
        ) - `LC_transactions (aggregated by {"CustomerID"}-{"CustomerID"}) (FDW 30 days)`.`LC_transactions (days since previous event by CustomerID) (30 days missing count)`
      ) - POW(
        `LC_transactions (aggregated by {"CustomerID"}-{"CustomerID"}) (FDW 30 days)`.`LC_transactions (days since previous event by CustomerID) (30 days sum)` / (
          coalesce(
            `LC_transactions (aggregated by {"CustomerID"}-{"CustomerID"}) (FDW 30 days)`.`LC_transactions (30 days count)`, 0
          ) - `LC_transactions (aggregated by {"CustomerID"}-{"CustomerID"}) (FDW 30 days)`.`LC_transactions (days since previous event by CustomerID) (30 days missing count)`
        ), 2
      )
    )     ELSE 0 END
  )
  AS `LC_transactions (days since previous event by CustomerID) (30 days std)`,
  
  dr_numeric_rounding(
    `LC_transactions (aggregated by {"CustomerID"}-{"CustomerID"}) (FDW 1 week)`.`date (days from LC_transactions[Date]) (1 week median)`
  )
  AS `date (days from LC_transactions[Date]) (1 week median)`,
  
  `DR_PRIMARY_TABLE`.`LC_profile[emp_title]`,
  
  dr_numeric_rounding(
    `LC_transactions (aggregated by {"CustomerID"}-{"CustomerID"}) (FDW 30 days)`.`date (days from LC_transactions[Date]) (30 days sum)`
  )
  AS `date (days from LC_transactions[Date]) (30 days sum)`,
  
  dr_map_to_json(
    `LC_transactions (aggregated by {"CustomerID"}-{"CustomerID"}) (FDW 1 week)`.`LC_transactions[Date] (Day of Month) (1 week value counts)`
  )
  AS `LC_transactions[Date] (Day of Month) (1 week counts)`,
  
  dr_numeric_rounding(
    coalesce(
      size(
        `LC_transactions (aggregated by {"CustomerID"}-{"CustomerID"}) (FDW 1 week)`.`LC_transactions[Description] (1 week value counts)`
      ), 0
    )
  )
  AS `LC_transactions[Description] (1 week unique count)`,
  
  `LC_transactions (aggregated by {"CustomerID"}-{"CustomerID"}) (FDW 30 days)`.`LC_transactions[Description] (30 days latest)`,
  
  dr_numeric_rounding(
    `DR_PRIMARY_TABLE`.`LC_profile[installment]`
  )
  AS `LC_profile[installment]`,
  
  dr_numeric_rounding(
    `LC_transactions (aggregated by {"CustomerID"}-{"CustomerID"}) (FDW 1 week)`.`date (days from LC_transactions[Date]) (1 week min)`
  )
  AS `date (days from LC_transactions[Date]) (1 week min)`,
  
  dr_map_to_json(
    `LC_transactions (aggregated by {"CustomerID"}-{"CustomerID"}) (FDW 30 days)`.`LC_transactions[Description] (30 days value counts)`
  )
  AS `LC_transactions[Description] (30 days counts)`,
  
  dr_numeric_rounding(
    coalesce(
      size(
        `LC_transactions (aggregated by {"CustomerID"}-{"CustomerID"}) (FDW 30 days)`.`LC_transactions[Date] (Day of Week) (30 days value counts)`
      ), 0
    )
  )
  AS `LC_transactions[Date] (Day of Week) (30 days unique count)`,
  
  dr_numeric_rounding(
    dr_entropy_from_map(
      `LC_transactions (aggregated by {"CustomerID"}-{"CustomerID"}) (FDW 30 days)`.`LC_transactions[Date] (Day of Week) (30 days value counts)`
    )
  )
  AS `LC_transactions[Date] (Day of Week) (30 days entropy)`,
  
  dr_numeric_rounding(
    dr_entropy_from_map(
      `LC_transactions (aggregated by {"CustomerID"}-{"CustomerID"}) (FDW 1 week)`.`LC_transactions[Date] (Day of Month) (1 week value counts)`
    )
  )
  AS `LC_transactions[Date] (Day of Month) (1 week entropy)`,
  
  dr_numeric_rounding(
    coalesce(
      size(
        `LC_transactions (aggregated by {"CustomerID"}-{"CustomerID"}) (FDW 1 week)`.`LC_transactions[Date] (Hour of Day) (1 week value counts)`
      ), 0
    )
  )
  AS `LC_transactions[Date] (Hour of Day) (1 week unique count)`,
  
  `DR_PRIMARY_TABLE`.`LC_profile[addr_state]`,
  
  `LC_transactions (aggregated by {"CustomerID"}-{"CustomerID"}) (FDW 30 days)`.`LC_transactions (days since previous event by CustomerID) (30 days missing count)`,
  
  dr_numeric_rounding(
    `LC_transactions (aggregated by {"CustomerID"}-{"CustomerID"}) (FDW 30 days)`.`date (days from LC_transactions[Date]) (30 days latest)`
  )
  AS `date (days from LC_transactions[Date]) (30 days latest)`,
  
  dr_numeric_rounding(
    `DR_PRIMARY_TABLE`.`LC_profile[int_rate]`
  )
  AS `LC_profile[int_rate]`,
  
  dr_numeric_rounding(
    `LC_transactions (aggregated by {"CustomerID"}-{"CustomerID"}) (FDW 1 week)`.`LC_transactions (days since previous event by CustomerID) (1 week median)`
  )
  AS `LC_transactions (days since previous event by CustomerID) (1 week median)`,
  
  dr_numeric_rounding(
    `LC_transactions (aggregated by {"CustomerID"}-{"CustomerID"}) (FDW 30 days)`.`date (days from LC_transactions[Date]) (30 days sum)` / (
      coalesce(
        `LC_transactions (aggregated by {"CustomerID"}-{"CustomerID"}) (FDW 30 days)`.`LC_transactions (30 days count)`, 0
      ) - `LC_transactions (aggregated by {"CustomerID"}-{"CustomerID"}) (FDW 30 days)`.`date (days from LC_transactions[Date]) (30 days missing count)`
    )
  )
  AS `date (days from LC_transactions[Date]) (30 days avg)`,
  
  dr_numeric_rounding(
    dr_entropy_from_map(
      `LC_transactions (aggregated by {"CustomerID"}-{"CustomerID"}) (FDW 1 week)`.`LC_transactions[Description] (1 week value counts)`
    )
  )
  AS `LC_transactions[Description] (1 week entropy)`,
  
  `DR_PRIMARY_TABLE`.`CustomerID`,
  
  `DR_PRIMARY_TABLE`.`LC_profile[funded_amnt]`,
  
  dr_numeric_rounding(
    `LC_transactions (aggregated by {"CustomerID"}-{"CustomerID"}) (FDW 1 week)`.`LC_transactions[Amount] (1 week sum)` / (
      coalesce(
        `LC_transactions (aggregated by {"CustomerID"}-{"CustomerID"}) (FDW 1 week)`.`LC_transactions (1 week count)`, 0
      ) - `LC_transactions (aggregated by {"CustomerID"}-{"CustomerID"}) (FDW 1 week)`.`LC_transactions[Amount] (1 week missing count)`
    )
  )
  AS `LC_transactions[Amount] (1 week avg)`,
  
  dr_numeric_rounding(
    `LC_transactions (aggregated by {"CustomerID"}-{"CustomerID"}) (FDW 1 week)`.`LC_transactions[Amount] (1 week max)`
  )
  AS `LC_transactions[Amount] (1 week max)`,
  
  dr_numeric_rounding(
    `LC_transactions (aggregated by {"CustomerID"}-{"CustomerID"}) (FDW 1 week)`.`LC_transactions[AccountID] (word count) (1 week sum)`
  )
  AS `LC_transactions[AccountID] (word count) (1 week sum)`,
  
  dr_numeric_rounding(
    `LC_transactions (aggregated by {"CustomerID"}-{"CustomerID"}) (FDW 1 week)`.`LC_transactions[Amount] (1 week sum)`
  )
  AS `LC_transactions[Amount] (1 week sum)`,
  
  `LC_transactions (aggregated by {"CustomerID"}-{"CustomerID"}) (FDW 30 days)`.`LC_transactions[AccountID] (30 days latest)`,
  
  `DR_PRIMARY_TABLE`.`LC_profile[sub_grade]`,
  
  `DR_PRIMARY_TABLE`.`LC_profile[grade]`,
  
  dr_numeric_rounding(
    `LC_transactions (aggregated by {"CustomerID"}-{"CustomerID"}) (FDW 1 week)`.`LC_transactions[Amount] (1 week median)`
  )
  AS `LC_transactions[Amount] (1 week median)`,
  
  dr_numeric_rounding(
    `LC_transactions (aggregated by {"CustomerID"}-{"CustomerID"}) (FDW 30 days)`.`LC_transactions (days since previous event by CustomerID) (30 days min)`
  )
  AS `LC_transactions (days since previous event by CustomerID) (30 days min)`,
  
  dr_numeric_rounding(
    CASE     WHEN `LC_transactions (aggregated by {"CustomerID"}-{"CustomerID"}) (FDW 30 days)`.`date (days from LC_transactions[Date]) (30 days sum of squares)` / (
      coalesce(
        `LC_transactions (aggregated by {"CustomerID"}-{"CustomerID"}) (FDW 30 days)`.`LC_transactions (30 days count)`, 0
      ) - `LC_transactions (aggregated by {"CustomerID"}-{"CustomerID"}) (FDW 30 days)`.`date (days from LC_transactions[Date]) (30 days missing count)`
    ) < 1e-11 THEN 0     WHEN POW(
      `LC_transactions (aggregated by {"CustomerID"}-{"CustomerID"}) (FDW 30 days)`.`date (days from LC_transactions[Date]) (30 days sum)` / (
        coalesce(
          `LC_transactions (aggregated by {"CustomerID"}-{"CustomerID"}) (FDW 30 days)`.`LC_transactions (30 days count)`, 0
        ) - `LC_transactions (aggregated by {"CustomerID"}-{"CustomerID"}) (FDW 30 days)`.`date (days from LC_transactions[Date]) (30 days missing count)`
      ), 2
    ) < 1e-11 OR        (
      (
        `LC_transactions (aggregated by {"CustomerID"}-{"CustomerID"}) (FDW 30 days)`.`date (days from LC_transactions[Date]) (30 days sum of squares)` / (
          coalesce(
            `LC_transactions (aggregated by {"CustomerID"}-{"CustomerID"}) (FDW 30 days)`.`LC_transactions (30 days count)`, 0
          ) - `LC_transactions (aggregated by {"CustomerID"}-{"CustomerID"}) (FDW 30 days)`.`date (days from LC_transactions[Date]) (30 days missing count)`
        )
      ) / (
        POW(
          `LC_transactions (aggregated by {"CustomerID"}-{"CustomerID"}) (FDW 30 days)`.`date (days from LC_transactions[Date]) (30 days sum)` / (
            coalesce(
              `LC_transactions (aggregated by {"CustomerID"}-{"CustomerID"}) (FDW 30 days)`.`LC_transactions (30 days count)`, 0
            ) - `LC_transactions (aggregated by {"CustomerID"}-{"CustomerID"}) (FDW 30 days)`.`date (days from LC_transactions[Date]) (30 days missing count)`
          ), 2
        )
      )
    ) > 1.00000000001        THEN SQRT(
      `LC_transactions (aggregated by {"CustomerID"}-{"CustomerID"}) (FDW 30 days)`.`date (days from LC_transactions[Date]) (30 days sum of squares)` / (
        coalesce(
          `LC_transactions (aggregated by {"CustomerID"}-{"CustomerID"}) (FDW 30 days)`.`LC_transactions (30 days count)`, 0
        ) - `LC_transactions (aggregated by {"CustomerID"}-{"CustomerID"}) (FDW 30 days)`.`date (days from LC_transactions[Date]) (30 days missing count)`
      ) - POW(
        `LC_transactions (aggregated by {"CustomerID"}-{"CustomerID"}) (FDW 30 days)`.`date (days from LC_transactions[Date]) (30 days sum)` / (
          coalesce(
            `LC_transactions (aggregated by {"CustomerID"}-{"CustomerID"}) (FDW 30 days)`.`LC_transactions (30 days count)`, 0
          ) - `LC_transactions (aggregated by {"CustomerID"}-{"CustomerID"}) (FDW 30 days)`.`date (days from LC_transactions[Date]) (30 days missing count)`
        ), 2
      )
    )     ELSE 0 END
  )
  AS `date (days from LC_transactions[Date]) (30 days std)`,
  
  `DR_PRIMARY_TABLE`.`date`,
  
  dr_numeric_rounding(
    `LC_transactions (aggregated by {"CustomerID"}-{"CustomerID"}) (FDW 30 days)`.`LC_transactions (days since previous event by CustomerID) (30 days sum)`
  )
  AS `LC_transactions (days since previous event by CustomerID) (30 days sum)`,
  
  dr_numeric_rounding(
    dr_entropy_from_map(
      `LC_transactions (aggregated by {"CustomerID"}-{"CustomerID"}) (FDW 30 days)`.`LC_transactions[Description] (30 days value counts)`
    )
  )
  AS `LC_transactions[Description] (30 days entropy)`,
  
  dr_numeric_rounding(
    `LC_transactions (aggregated by {"CustomerID"}-{"CustomerID"}) (FDW 30 days)`.`LC_transactions (days since previous event by CustomerID) (30 days median)`
  )
  AS `LC_transactions (days since previous event by CustomerID) (30 days median)`,
  
  dr_get_max_value_key(
    `LC_transactions (aggregated by {"CustomerID"}-{"CustomerID"}) (FDW 30 days)`.`LC_transactions[Date] (Day of Week) (30 days value counts)`
  )
  AS `LC_transactions[Date] (Day of Week) (30 days most frequent)`,
  
  dr_numeric_rounding(
    CASE     WHEN `LC_transactions (aggregated by {"CustomerID"}-{"CustomerID"}) (FDW 1 week)`.`date (days from LC_transactions[Date]) (1 week sum of squares)` / (
      coalesce(
        `LC_transactions (aggregated by {"CustomerID"}-{"CustomerID"}) (FDW 1 week)`.`LC_transactions (1 week count)`, 0
      ) - `LC_transactions (aggregated by {"CustomerID"}-{"CustomerID"}) (FDW 1 week)`.`date (days from LC_transactions[Date]) (1 week missing count)`
    ) < 1e-11 THEN 0     WHEN POW(
      `LC_transactions (aggregated by {"CustomerID"}-{"CustomerID"}) (FDW 1 week)`.`date (days from LC_transactions[Date]) (1 week sum)` / (
        coalesce(
          `LC_transactions (aggregated by {"CustomerID"}-{"CustomerID"}) (FDW 1 week)`.`LC_transactions (1 week count)`, 0
        ) - `LC_transactions (aggregated by {"CustomerID"}-{"CustomerID"}) (FDW 1 week)`.`date (days from LC_transactions[Date]) (1 week missing count)`
      ), 2
    ) < 1e-11 OR        (
      (
        `LC_transactions (aggregated by {"CustomerID"}-{"CustomerID"}) (FDW 1 week)`.`date (days from LC_transactions[Date]) (1 week sum of squares)` / (
          coalesce(
            `LC_transactions (aggregated by {"CustomerID"}-{"CustomerID"}) (FDW 1 week)`.`LC_transactions (1 week count)`, 0
          ) - `LC_transactions (aggregated by {"CustomerID"}-{"CustomerID"}) (FDW 1 week)`.`date (days from LC_transactions[Date]) (1 week missing count)`
        )
      ) / (
        POW(
          `LC_transactions (aggregated by {"CustomerID"}-{"CustomerID"}) (FDW 1 week)`.`date (days from LC_transactions[Date]) (1 week sum)` / (
            coalesce(
              `LC_transactions (aggregated by {"CustomerID"}-{"CustomerID"}) (FDW 1 week)`.`LC_transactions (1 week count)`, 0
            ) - `LC_transactions (aggregated by {"CustomerID"}-{"CustomerID"}) (FDW 1 week)`.`date (days from LC_transactions[Date]) (1 week missing count)`
          ), 2
        )
      )
    ) > 1.00000000001        THEN SQRT(
      `LC_transactions (aggregated by {"CustomerID"}-{"CustomerID"}) (FDW 1 week)`.`date (days from LC_transactions[Date]) (1 week sum of squares)` / (
        coalesce(
          `LC_transactions (aggregated by {"CustomerID"}-{"CustomerID"}) (FDW 1 week)`.`LC_transactions (1 week count)`, 0
        ) - `LC_transactions (aggregated by {"CustomerID"}-{"CustomerID"}) (FDW 1 week)`.`date (days from LC_transactions[Date]) (1 week missing count)`
      ) - POW(
        `LC_transactions (aggregated by {"CustomerID"}-{"CustomerID"}) (FDW 1 week)`.`date (days from LC_transactions[Date]) (1 week sum)` / (
          coalesce(
            `LC_transactions (aggregated by {"CustomerID"}-{"CustomerID"}) (FDW 1 week)`.`LC_transactions (1 week count)`, 0
          ) - `LC_transactions (aggregated by {"CustomerID"}-{"CustomerID"}) (FDW 1 week)`.`date (days from LC_transactions[Date]) (1 week missing count)`
        ), 2
      )
    )     ELSE 0 END
  )
  AS `date (days from LC_transactions[Date]) (1 week std)`,
  
  dr_numeric_rounding(
    `LC_transactions (aggregated by {"CustomerID"}-{"CustomerID"}) (FDW 30 days)`.`LC_transactions[Amount] (30 days median)`
  )
  AS `LC_transactions[Amount] (30 days median)`,
  
  dr_numeric_rounding(
    `LC_transactions (aggregated by {"CustomerID"}-{"CustomerID"}) (FDW 30 days)`.`LC_transactions[Amount] (30 days max)`
  )
  AS `LC_transactions[Amount] (30 days max)`,
  
  dr_map_to_json(
    `LC_transactions (aggregated by {"CustomerID"}-{"CustomerID"}) (FDW 1 week)`.`LC_transactions[AccountID]  (1 week token counts)`
  )
  AS `LC_transactions[AccountID] (1 week tokens)`,
  
  `DR_PRIMARY_TABLE`.`LC_profile[emp_length]`,
  
  dr_numeric_rounding(
    `LC_transactions (aggregated by {"CustomerID"}-{"CustomerID"}) (FDW 30 days)`.`LC_transactions[AccountID] (word count) (30 days sum)`
  )
  AS `LC_transactions[AccountID] (word count) (30 days sum)`,
  
  dr_map_to_json(
    `LC_transactions (aggregated by {"CustomerID"}-{"CustomerID"}) (FDW 1 week)`.`LC_transactions[Description] (1 week value counts)`
  )
  AS `LC_transactions[Description] (1 week counts)`,
  
  dr_get_max_value_key(
    `LC_transactions (aggregated by {"CustomerID"}-{"CustomerID"}) (FDW 1 week)`.`LC_transactions[Date] (Day of Month) (1 week value counts)`
  )
  AS `LC_transactions[Date] (Day of Month) (1 week most frequent)`,
  
  `DR_PRIMARY_TABLE`.`LC_profile[zip_code]`

FROM (

  (
  
    `featurized DR_PRIMARY_TABLE (lookup only) (view)` AS `DR_PRIMARY_TABLE`
    
  )
  LEFT JOIN (
  
    `featurized LC_transactions (aggregated by {"CustomerID"}-{"CustomerID"}) (FDW 1 week) (1 week) (view)` AS `LC_transactions (aggregated by {"CustomerID"}-{"CustomerID"}) (FDW 1 week)`
    
  ) AS `LC_transactions (aggregated by {"CustomerID"}-{"CustomerID"}) (FDW 1 week)`
  
  ON
  
    `DR_PRIMARY_TABLE`.`CustomerID` = `LC_transactions (aggregated by {"CustomerID"}-{"CustomerID"}) (FDW 1 week)`.`CustomerID` AND
    `DR_PRIMARY_TABLE`.`SAFER_CUTOFF_598d7e6ae89bde0eadd7456a_1_MINUTE` = `LC_transactions (aggregated by {"CustomerID"}-{"CustomerID"}) (FDW 1 week)`.`SAFER_CUTOFF_598d7e6ae89bde0eadd7456a`
)
LEFT JOIN (

  `featurized LC_transactions (aggregated by {"CustomerID"}-{"CustomerID"}) (FDW 30 days) (30 days) (view)` AS `LC_transactions (aggregated by {"CustomerID"}-{"CustomerID"}) (FDW 30 days)`
  
) AS `LC_transactions (aggregated by {"CustomerID"}-{"CustomerID"}) (FDW 30 days)`

ON

  `DR_PRIMARY_TABLE`.`CustomerID` = `LC_transactions (aggregated by {"CustomerID"}-{"CustomerID"}) (FDW 30 days)`.`CustomerID` AND
  `DR_PRIMARY_TABLE`.`SAFER_CUTOFF_598d7e6ae89bde0eadd7456a_1_MINUTE` = `LC_transactions (aggregated by {"CustomerID"}-{"CustomerID"}) (FDW 30 days)`.`SAFER_CUTOFF_598d7e6ae89bde0eadd7456a`

ORDER BY

  `dr_row_idx`

/*
BLOCK END -- Create "DR_PRIMARY_TABLE" table with engineered features
*/
