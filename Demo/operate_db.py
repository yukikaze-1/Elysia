
from pymilvus import MilvusClient
from Demo.Utils import create_embedding_model, create_memory_collection

milvus_client = MilvusClient(uri="http://localhost:19530", token="root:Milvus")
collection_name = "l2_associative_memory"

def search():
    res = milvus_client.query(
        collection_name=collection_name,
        filter="",
        limit=100,
        output_fields=["id", "content", "poignancy", "keywords", "timestamp"]
    )

    for hit in res:
        print(hit)
        
    res = milvus_client.query(
            collection_name=collection_name,
            output_fields=["count(*)"],
    )
    print(f"Total memories: {res[0]}")

from Demo.test_dataset import embedded_abstract_memories


def inject_data():
    memories = embedded_abstract_memories
    if not milvus_client.has_collection(collection_name):
        print(f"Error! No collection named {collection_name}! Exited.")
        return
    contents: list[str] = [memory['content'] for memory in memories]
    model = create_embedding_model()
    vecs: list[list[float]] = model.embed_documents(contents)
    
    # for mem, vec in zip(memories, vecs):
    #     mem["embedding"] = vec
    
    data = []
    
    for mem, vec in zip(memories, vecs):
        if mem['poignancy'] < 3: continue # 过滤掉琐事
        info = {
            "content": mem['content'],
            "embedding": vec,
            "type": mem['type'],
            "poignancy": mem['poignancy'],
            "keywords": mem['keywords'],
            "timestamp": int(mem['timestamp'])
        }
        data.append(info)
    # 插入
    res = milvus_client.insert(collection_name="l2_associative_memory", data=data)
    print(f"Stored {len(data)} new memories.\n {res}")    
    
    
def clean_up_collection():
    if milvus_client.has_collection(collection_name):
        print(f"Drop collection {collection_name}.")
        milvus_client.drop_collection(collection_name)
        print(f"Creating collection {collection_name}.")
        create_memory_collection(collection_name, milvus_client)
        
        
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
    elif args.command == "inject":
        inject_data()
    elif args.command == "search":
        search()
    else:
        print("Invalid operator.")