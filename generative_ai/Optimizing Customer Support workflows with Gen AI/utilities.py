import networkx as nx
import pandas as pd


def get_documents(source_file, destination_folder):
    # filter data
    df_tweets = pd.read_csv(source_file)
    org = "AskSeagate"
    tweets = df_tweets[(df_tweets.text.str.find(org) != -1) | (df_tweets.author_id == org)]
    # create conversation threads
    df = tweets[~tweets["in_response_to_tweet_id"].isna()][
        ["tweet_id", "in_response_to_tweet_id"]
    ].copy(deep=True)
    df.columns = ["CHILD", "PARENT"]
    G = nx.from_pandas_edgelist(df, "CHILD", "PARENT")
    l = list(nx.connected_components(G))
    # write documents to file
    counter = 0
    for i in l:
        i = list(i)
        i.reverse()
        conversation = "\n\n".join(df_tweets[df_tweets.tweet_id.isin(i)].text.values)
        conversation = conversation.replace("Seagate", "AwesomeStore").replace(
            "seagate", "AwesomeStore"
        )
        file = open(destination_folder + "/conversation_" + str(counter) + ".txt", "a")
        file.write(conversation)
        file.close()
        counter += 1
    return True
