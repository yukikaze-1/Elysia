
from pymilvus import MilvusClient
from Demo.Utils import create_embedding_model, create_micro_memory_collection, create_macro_memory_collection

milvus_client = MilvusClient(uri="http://localhost:19530", token="root:Milvus")
collection_name = "micro_memory"

# def search():
#     res = milvus_client.query(
#         collection_name=collection_name,
#         filter="timestamp > 1766431571 AND poignancy >= 3",
#         # filter="",
#         limit=100,
#         output_fields=["id", "memory_type", "content", "poignancy", "keywords", "timestamp"],
#         consistency_level="Strong"
#     )

#     for hit in res:
#         print(hit)
        
#     res = milvus_client.query(
#             collection_name=collection_name,
#             output_fields=["count(*)"],
#     )
#     print(f"Total memories: {res[0]}")

def search():
    res = milvus_client.query(
        collection_name="macro_memory",
        # filter="timestamp > 1766431571 AND poignancy >= 3",
        filter="",
        limit=100,
        output_fields=["id", "diary_content", "poignancy", "keywords", "timestamp"],
        consistency_level="Strong"
    )

    for hit in res:
        print(hit)
        
    res = milvus_client.query(
            collection_name="macro_memory",
            output_fields=["count(*)"],
    )
    print(f"Total memories: {res[0]}")
    
def clean_up_collection():
    if milvus_client.has_collection(collection_name):
        print(f"Drop collection {collection_name}.")
        milvus_client.drop_collection(collection_name)
        print(f"Creating collection {collection_name}.")
        create_micro_memory_collection(collection_name, milvus_client)
        
        
if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(
        dest="command",
        required=True
    )
    subparsers.add_parser("clean")
    subparsers.add_parser("inject")
    subparsers.add_parser("search")
    
    args = parser.parse_args()
    
    if args.command == "clean":
        clean_up_collection()
    elif args.command == "search":
        search()
    else:
        print("Invalid operator.")