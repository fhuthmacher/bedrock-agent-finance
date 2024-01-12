# Amazon Bedrock Agents Finance

Welcome to the Amazon Bedrock Agents Tutorial. In this tutorial, you will first learn how to create a chat application that retrieves financial information from the internet for a given company to provide investment advice leveraging an Amazon Bedrock agent dubbed "Agent Finance". Then we will instrument the application and incorporate observability with Amazon OpenSearch.

By the end of this tutorial, you will have gained valuable hands-on experience in building Amazon Bedrock Agents and incorporating observability.

![Agent Architecture Diagram](/images/agent_arch.png)

Some familiarly with Python and using services such as Lambda and Elastic Container Registry is helpful. No AI/ML experience is necessary.

## Prerequisites

This tutorial assumes you are working in an environment with access to [Python 3.9](https://www.python.org/getit/) or later and [Docker](https://www.docker.com/). 

## Deployment instructions
If you want to deploy the entire solution with IaC, log into your AWS management console. Then click the Launch Stack button below to deploy the required resources.

[![Launch CloudFormation Stack](https://felixh-github.s3.amazonaws.com/misc_public/launchstack.png)](https://console.aws.amazon.com/cloudformation/home#/stacks/new?stackName=agentfinance&templateURL=https://felixh-github.s3.amazonaws.com/misc_public/bedrock-finance-agent.yml)

Alternatively follow  the high-level steps in the blog post.

The CloudFormation stack will create following resources in your account:
- Amazon Simple Storage Service (Amazon S3) bucket
- Glue database, crawler, and table for sample dataset
- 3 AWS Lambda functions & layers
- 3 IAM roles
- Elastic Container RegistryBedrock Knowledge Base & Bedrock Agent
- OpenSearch Serverless Collection as backend for Bedrock KB
- Provisioned OpenSearch cluster for observability
- OpenSearch Ingestion pipeline for observability
- temporary EC2 instance to pull and push Docker image to ECR

To avoid incurring additional charges to your account, stop and delete all of the resources by deleting the CloudFormation template at the end of this tutorial.