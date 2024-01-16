FROM amazon/aws-lambda-python:3.11

ARG AWS_DEFAULT_REGION=${AWS_DEFAULT_REGION:-"us-east-1"}
ARG AWS_ACCESS_KEY_ID=${AWS_ACCESS_KEY_ID:-""}
ARG AWS_SECRET_ACCESS_KEY=${AWS_SECRET_ACCESS_KEY:-""}
ENV AWS_DEFAULT_REGION=${AWS_DEFAULT_REGION}
ENV AWS_ACCESS_KEY_ID=${AWS_ACCESS_KEY_ID}
ENV AWS_SECRET_ACCESS_KEY=${AWS_SECRET_ACCESS_KEY}

RUN yum install unzip aws-cli -y

RUN mkdir -p /opt

RUN curl $(aws lambda get-layer-version-by-arn --arn arn:aws:lambda:us-east-1:901920570463:layer:aws-otel-python-amd64-ver-1-21-0:1 --query 'Content.Location' --output text) --output layer.zip
RUN unzip layer.zip -d /opt
RUN rm layer.zip

# Install deps
COPY requirements.txt ${LAMBDA_TASK_ROOT}

RUN pip install --upgrade pip
RUN pip install -r requirements.txt
RUN pip install -U boto3 botocore

# Copy function code
COPY index.py ${LAMBDA_TASK_ROOT}
COPY tools.py ${LAMBDA_TASK_ROOT}
COPY collector.yml ${LAMBDA_TASK_ROOT}

# Set the CMD to your handler
CMD [ "index.handler" ]