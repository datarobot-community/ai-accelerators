import re


def generate_links(locs, max_links=None):
    dr_docs_dir = "storage/vectordb_training/datarobot_docs/en/"
    dr_security_dir = "storage/vectordb_training/datarobot_docs/"
    rfp_docs_dir = "storage/vectordb_training/reprocessed_data/"
    links = []
    for link in locs:
        if link.startswith(dr_docs_dir):
            link = link[len(dr_docs_dir) :]
            link = "https://docs.datarobot.com/en/docs/" + link
            link = link[:-2] + "html"  # Remove "md", add html
        elif link.startswith(dr_security_dir):
            link = "https://www.datarobot.com/trustcenter/"
        elif link.startswith(rfp_docs_dir):
            try:
                file = open(link, "r")
                file_contents = file.read()
                link = re.search(r"https://\S+", file_contents)
                file.close()
                link = link.group()
            except AttributeError:
                print("Attribute error")
                link = None
                pass
            except FileNotFoundError:
                link = None
                pass
        links.append(link)
    links = list(set([link for link in links if link != None]))
    return links
