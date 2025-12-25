
from typing import Literal
from pymilvus import MilvusClient
from .Utils import create_embedding_model, create_micro_memory_collection, create_macro_memory_collection

milvus_client = MilvusClient(uri="http://localhost:19530", token="root:Milvus")
micro_memory_collection_name = "micro_memory"
macro_memory_collection_name = "macro_memory"


def search(type: Literal["micro", "macro"]):
    if type == "micro":
        search_micro()
    else:
        search_macro()
    

def search_micro():
    res = milvus_client.query(
        collection_name=micro_memory_collection_name,
        filter="timestamp > 1766431571 AND poignancy >= 3",
        # filter="",
        limit=100,
        output_fields=["id", "memory_type", "content", "poignancy", "keywords", "timestamp"],
        consistency_level="Strong"
    )

    for hit in res:
        print(hit)
        
    res = milvus_client.query(
            collection_name=micro_memory_collection_name,
            output_fields=["count(*)"],
    )
    print(f"Total memories: {res[0]}")

def search_macro():
    res = milvus_client.query(
        collection_name=macro_memory_collection_name,
        # filter="timestamp > 1766431571 AND poignancy >= 3",
        filter="",
        limit=100,
        output_fields=["id", "diary_content", "poignancy", "keywords", "timestamp"],
        consistency_level="Strong"
    )

    for hit in res:
        print(hit)
        
    res = milvus_client.query(
            collection_name=macro_memory_collection_name,
            output_fields=["count(*)"],
    )
    print(f"Total memories: {res[0]}")
    
    
def clean_up_collection():
    # 删除并重新创建micro memory集合
    if milvus_client.has_collection(micro_memory_collection_name):
        print(f"Drop collection {micro_memory_collection_name}.")
        milvus_client.drop_collection(micro_memory_collection_name)
        print(f"Creating collection {micro_memory_collection_name}.")
        create_micro_memory_collection(micro_memory_collection_name, milvus_client)
        
    if milvus_client.has_collection(macro_memory_collection_name):
        print(f"Drop collection {macro_memory_collection_name}.")
        milvus_client.drop_collection(macro_memory_collection_name)
        print(f"Creating collection {macro_memory_collection_name}.")
        create_macro_memory_collection(macro_memory_collection_name, milvus_client)
        
        
if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    
    # 一级子命令
    subparsers = parser.add_subparsers(
        dest="command",
        required=True
    )
    # clean 命令
    subparsers.add_parser("clean")
    
    # search 命令
    search_parser = subparsers.add_parser("search")

    # 二级子命令
    search_subparsers = search_parser.add_subparsers(
        dest="search_type",
        required=True
    )

    search_subparsers.add_parser("micro")
    search_subparsers.add_parser("macro")
    
    args = parser.parse_args()
    
    
    if args.command == "clean":
        clean_up_collection()
    elif args.command == "search":
        search(args.search_type)
    else:
        print("Invalid operator.")