# Overview

This repository aims to showcase how you can setup a simple web app in AWS EKS for EC2, using kubectl, eksctl and the AWS CLI. It uses EKS Pod Identity for giving permissions to pods to use AWS resources, rather than Cluster or Node IAM roles. 

##### Pre-requsites:

Access to an AWS account with full priveliges. Note that following these instructions will incur charges onto your AWS account.

##### This repository contains:

1. a CloudFormation template that sets up a Cloud9 development environment for working with EKS (it's also possible to do this from your local machine, but then you have to install eksctl, kubectl and the AWS CLI yourself)
2. source files for building a docker image that contains a simple web app that will return a value retrieved from DynamoDB
3. CloudFormation templates that set up a DynamoDB table and permissions for an EKS Pod Identity.
4. source files for deploying an EKS cluster, as well as Kubernetes specific resources (deployment, ingress, namespace, service account, service)

# What will the final setup look like?

![Architecture diagram](/eks-pod-identity-sample/documentation/arch-eks-sample.png)
By deploying this setup in your AWS account, you will be able to access a web server through a load balancer. By calling the load balancer endpoint, you should be able to retrieve a value stored in DynamoDB. The web server will retrieve the object from DynamoDB using permissions granted through EKS Pod Identity. 

# Instrutions

##### 1. Clone this repository

Clone this repository and then step into the newly cloned folder (`web-server-app`).

##### 2. (Optional) for using Cloud9 as your development environment

Setup the Cloud9 development environment by deploying the `/cfn/cloud9-env-cfn.yaml` CloudFormation stack using the following command:

```
aws cloudformation deploy \
--stack-name eks-sample-cloud9-dev-env-ide \
--template-file ./cfn/cloud9-env-cfn.yaml \
--capabilities CAPABILITY_NAMED_IAM
```

After setting up the Cloud9 dev environment. Clone this repository (`drahtesel2024/eks-pod-identity-sample`) into the Cloud9 environment so you have access to all the source files that we're going to be using for the next steps.

##### 3. Create the AWS Load Balancer Controller IAM Policy

Follow the instructions [here](https://kubernetes-sigs.github.io/aws-load-balancer-controller/v2.7/deploy/installation/) under "Configure IAM" (Option A) to create the IAM policy. Start by doing steps 1-3. Before moving on to the fourth step, we need to first create the EKS cluster. Also, note what version of the AWS Load Balancer Controller you're using, this tutorial was built using v2.7. Later versions might also work.

##### 4. Modify the cluster.yaml file

Go into your AWS Console and retrieve the ARN for the AWS Load Balancer Controller IAM policy you just created. It should be called `AWSLoadBalancerControllerIAMPolicy`. Replace the placeholder value and add this to the `attachPolicyARNs` field in the ```/kubernetes/cluster.yaml``` file.


##### 5. Create the EKS cluster

Execute the following command to create the EKS cluster:

```
eksctl create cluster -f ./kubernetes/cluster.yaml
```

##### 6. Create IAM role and Kubernetes service account for the load balancer controller

Complete step 4 in [this guide](https://kubernetes-sigs.github.io/aws-load-balancer-controller/v2.7/deploy/installation/) under "Configure IAM" (Option A).

##### 7. Add the AWS Load Balancer Controller to your cluster

We're going to use Helm for this step. It can also be done using YAML manifests. Follow the steps under "Add controller to cluster" [here](https://kubernetes-sigs.github.io/aws-load-balancer-controller/v2.7/deploy/installation/). We'll go with the "install command for clusters with IRSA" option, since we did the setup using IAM roles for service accounts (IRSA).

You can verify that the load balancer controller is up and running by executing the following command:

```
kubectl get deployments \
-n kube-system
```

##### 8. Build the container image and upload it to ECR

Create the repository using the following CLI command, or using the AWS management console.

```
aws ecr create-repository --repository-name sample-web-server
```

Then go into the AWS management console and click on the newly created "sample-web-server" repository. After doing this, select "View push commands" in the upper right corner and follow those steps for building and uploading the container image to the repository. Note that the instructions listed there assume that you're positioned in the  `/sample-app` directory. I.e. the directory containing the Dockerfile and relevant container image source files.

If you rebuild the image and want to remove all the 'dangling'/unused images on your system (Cloud9 or local machine), you may run the following command:

```
sudo docker rmi $(docker images -f "dangling=true" -q)
```

For the rest of this walkthrough, make sure you're in the root directory of this repository. Usually, it should be named `/eks-pod-identity-sample`.

##### 9. Create a DynamoDB Table

This table will be accessed by the web server containers running in pods in the EKS cluster.

```
aws cloudformation deploy \
--stack-name eks-sample-ddb \
--template-file ./cfn/ddb-cfn.yaml
```

##### 10. Populate the DynamoDB Table

Add one item to the DynamoDB table manually. This can be done from the management console. Give it the partition key (pk), "key", and add a string attribute with the name "value". Have the value of this attribute be "hello world!". See the screenshot below for reference.

!["dynamodb add item"](/eks-pod-identity-sample/documentation/dynamodb-add-item.png)

##### 11. Update the `deployment.yaml` file.

In `/kubernetes/deployment.yaml`, under spec->template->spec->containers->image, change the placeholder value for "image". The new value should be the URI found in the AWS management console for the newly created repository "sample-web-server". The image tag will have the value "latest". It will be in the shape of
```<aws account number>.dkr.ecr.<region>.amazonaws.com/sample-web-server:latest```.

##### 12. Add the EKS Pod Identity Agent

We add the EKS Pod Identity Agent in order to manage credentials for our EKS applications. Amazon EKS Pod Identity provides credentials for our workloads with an additional EKS Auth API and an agent pod that runs on each node. 

Follow the steps [here](https://docs.aws.amazon.com/eks/latest/userguide/pod-id-agent-setup.html) to setup the agent.

##### 13. Deploy the namespace

Deploy the namespace using:

```
kubectl apply -f ./kubernetes/namespace.yaml
```

##### 14. Confugre the IAM role and the service account 

Deploy the service account using:

```
kubectl apply -f ./kubernetes/service-account.yaml
```

Deploy the `eks-pod-identity-cfn.yaml` file using:

```
aws cloudformation deploy \
--stack-name eks-pod-identity-permissions \
--template-file ./cfn/pod-identity-policy-and-role-cfn.yaml \
--capabilities CAPABILITY_IAM
```
##### 15. Create the association between the service account and the newly created role

Execute the following command (you can find the role in the 'Resources' tab of the `eks-pod-identity-permissions` cloudformation deployment, clicking on it should take you to a page form which the role ARN can be copied):

```
aws eks create-pod-identity-association \
--cluster-name eks-sample \
--role-arn <ROLE ARN> \
--namespace eks-sample \
--service-account sample-service-account
```

Verify the newly created association using:

```
aws eks list-pod-identity-associations \
--cluster-name eks-sample
```

Verify the assocation between the service account and the IAM role:

```
aws eks describe-pod-identity-association \
--cluster-name eks-sample \
--association-id <ASSOCATION ID>
```

If something went wrong, (eg, if you recreate the IAM role), you might delete the newly created assocation using:

```
aws eks delete-pod-identity-association \
--cluster-name eks-sample \
--association-id <ASSOCATION ID>
```

##### 16. Deploy pods

Deploy the sample-app using:

```
kubectl apply -f ./kubernetes/deployment.yaml
```

We can verify the deployment using:

```
kubectl get deployment -n eks-sample
```

If something gets messed up by accident, the deployment can be deleted using:

```
kubectl delete deployment -n eks-sample sample-deployment
```

We can verify that the pods deployed with the correct association to the service account by:

First, getting the name of a pod from the deployment:
    
```
kubectl get pods -n eks-sample | grep sample-web-server
```

And then, verifying that there is a token file associated with the pod:

```
kubectl describe pod <POD NAME> -n eks-sample | grep AWS_CONTAINER_AUTHORIZATION_TOKEN_FILE:
```

**Having configured the EKS Pod Identity, the Pod Identity credentials will be used by default if no other credential provider is specified when you create or otherwise initialise the SDK in the pod.**

##### 18. Deploy the rest of the application

Deploy the service and the ingress.

```
kubectl apply -f ./kubernetes/service.yaml
kubectl apply -f ./kubernetes/ingress.yaml
```

We can verify these deployment using the following:

```
kubectl get service -n eks-sample
kubectl get ingress -n eks-sample
```

If something gets messed up by accident, these can be deleted using:

```
kubectl delete service -n eks-sample sample-service
kubectl delete ingress -n eks-sample sample-ingress
```

### Troubleshooting

##### Trouble with credentials (retrieving object from DynamoDB)

Check the association. If you recreated the IAM role, the assocation might still be to an older version of the role. Fix this by:

1) redeploying the service account
2) redeploying the service
3) re-associating the service account to the recreated IAM role
4) redeploying the deployment


### Tear everything down...

If you want to delete everything you've deployed following these instructions, use the following:

```
kubectl delete serviceaccount -n eks-sample sample-service-account
kubectl delete deployment -n eks-sample sample-deployment
kubectl delete service -n eks-sample sample-service
kubectl delete ingress -n eks-sample sample-ingress
kubectl delete pod -n eks-sample pod-with-aws-access
kubectl delete serviceaccount -n eks-sample sample-service-account
kubectl delete namespace eks-sample
```

You can delete the cluster using the instructions [here](https://docs.aws.amazon.com/eks/latest/userguide/delete-cluster.html).

You can tear down the CloudFormation deployments using the following steps.

1. Verify the stack names with:
```
aws cloudformation list-stacks --stack-status-filter CREATE_COMPLETE
```
2. Find the stacks you want to delete and then repeat step 3.
3. Execute the following command:
```
aws cloudformation delete-stack --stack-name <stack-name>
```

You can also delete the stacks from the management console.


##### If you want to verify how credentials are evaluated for a pod...

Deploy the test pod using:

```
kubectl apply -f ./kubernetes/test-pod.yaml
```

Execute the following command to check where credentials will be looked for:

```
kubectl exec pod/pod-with-aws-access -n eks-sample -- \
python -c "import boto3, logging; boto3.set_stream_logger('botocore.credentials', logging.DEBUG); print(boto3.client('sts').get_caller_identity()['Arn'])"
```

Delete the pod after testing:

```
kubectl delete pods pod-with-aws-access -n eks-sample
```