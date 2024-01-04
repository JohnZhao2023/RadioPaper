# Usage
- These are the codes for the agent-based hybrid cloud system

# How to use it
- The folder "private_cloud" is for deployment on the private cloud
- The folder "public_cloud" is for deployment on the public cloud

## for direct run
- on the private cloud, please run "pip install --no-cache-dir -r ./requirements-private.txt", and then run "python3 private_cloud.py"
- on the public cloud, please run "pip install --no-cache-dir -r ./requirements-public.txt", and then run "python3 public_cloud.py"
- please run the public_cloud.py first, then run the private_cloud.py"
- input the questions according to the input prompt, and then return the answer
- for the private and public cloud, the relevant yaml file is for the params input, the meaning of the params is as below:
    1. public-server-port: it represent the port for communication on the public server, it should be an int number
    2. private-server-port: it represent the port for communication on the private server, it should be an int number, please note, the public-server-port and the private-server-port on both yaml files should be the same
    3. public-server-address: it represent the ipv4 address of the public server, it should be a string, and it is configured on the yaml on the private cloud
    4. openai_api_key: it represents the openai api key for using openai API service, it should be a string, and it is configured on the yaml on the public cloud

## for docker deployment
- first please install docker and relevant configuration
- the usage of yaml is the same with the direct run
- on the private cloud, the procedures should be as below:
    1. establish a docker image with the name "private-cloud-img":
    docker build -t private-cloud-img . -f Dockerfile-private
    2. run the command "docker run" to start the "private-cloud-img" image:
    docker run -it -p {private-server-port}:{private-server-port} --name private-service private-cloud-img
    please note, the param "-it" should be included to make the docker interact with the window for the question input, -p is for port mapping from the docker to the host
    3. use the service as the direct run
- on the public cloud, the procedures should be as below:
    1. establish a docker image with the name "public-cloud-img":
    docker build -t public-cloud-img . -f Dockerfile-public
    2. run the command "docker run" to start the "public-cloud-img" image:
    docker run -it -p {public-server-port}:{public-server-port} --name public-service public-cloud-img
    3. use the service as the direct run

# Things to be noticed
- For the protection of private information (openai API key, private/public cloud ip address, etc.), NO private information will be occuring in the codes, it will be only configured by users on the yaml files
