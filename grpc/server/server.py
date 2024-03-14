from kubernetes import client, config
from concurrent import futures
import grpc
import ai_pb2
import ai_pb2_grpc

# 加载Kubernetes配置，如果是在集群内部署，则使用in-cluster配置
# 对于本地开发，使用kubeconfig文件
config.load_kube_config()  # 对于集群内部署，请使用config.load_incluster_config()

# 创建Kubernetes API客户端
k8s_client = client.CustomObjectsApi()

def get_rbac_reply_mapping():
    # 获取CRD信息
    print("fetch CRD")
    namespace = "default"  # 假定CRD在default命名空间
    crd_group = "example.com"
    crd_version = "v1"
    crd_plural = "grpcreplyrules"

    try:
        crd_instance = k8s_client.get_namespaced_custom_object(
            group=crd_group,
            version=crd_version,
            namespace=namespace,
            plural=crd_plural,
            name="example-reply-rule"
        )
        rules = crd_instance.get("spec", {}).get("rules", [])
        # 将规则映射为token到message的字典
        return {rule["token"]: rule["message"] for rule in rules}
    except client.exceptions.ApiException as e:
        print(f"An error occurred while fetching CRD: {e}")
        return {}

def get_role_from_token(token):
    # 这个函数可以根据需要实现，这里简化为直接从CRD映射获取
    role_reply_mapping = get_rbac_reply_mapping()
    return role_reply_mapping.get(token, "Unknown token")

class ReplyService(ai_pb2_grpc.ReplyServiceServicer):
    def GetReply(self, request, context):
        print("run ReplyService")
        #return ai_pb2.ReplyResponse(message="Pong")
        if request.status == ai_pb2.UNRAG_REQUEST:
            reply_message = get_role_from_token(request.token)
            return ai_pb2.ReplyResponse(message=reply_message,status=ai_pb2.PRIVATE_AGENT_RESPONSE)

def intercept_call(servicer, call_details, request_iterator):
    # 由于这是一个静态拦截器的示例，这里不做修改，保持原有逻辑
    print("intercept")
    return servicer(call_details, request_iterator)

def serve():
    #server = grpc.server(futures.ThreadPoolExecutor(max_workers=100),
    #                     interceptors=(intercept_call,))
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    error=ai_pb2_grpc.add_ReplyServiceServicer_to_server(ReplyService(), server)
    print(error)
    server.add_insecure_port('[::]:50051')
    #server.add_insecure_port('10.221.120.210:50051')
    print("AI agent Server is starting..")
    server.start()
    server.wait_for_termination()

if __name__ == '__main__':
    serve()

