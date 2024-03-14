# client.py
import grpc
import ai_pb2
import ai_pb2_grpc

def run():
    with grpc.insecure_channel('10.221.120.210:50051') as channel:
        stub = ai_pb2_grpc.ReplyServiceStub(channel)
        response = stub.GetReply(ai_pb2.ReplyRequest(token='token3', status=ai_pb2.UNRAG_REQUEST))
        print("Client received: " + response.message)
        print(response.status)

if __name__ == '__main__':
    run()

