import tools
import os 
#from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry import trace
from opentelemetry import metrics

### Explicitly added for logging which is currently in experimental stage and not working with auto-instrumentation
### OTEL_PYTHON_LOGGING_AUTO_INSTRUMENTATION_ENABLED = true
### BEG
import logging
from opentelemetry._logs import get_logger
from opentelemetry._logs import get_logger_provider
from opentelemetry._logs import set_logger_provider
from opentelemetry.exporter.otlp.proto.http._log_exporter import (
   OTLPLogExporter,
)
from opentelemetry.sdk._logs import LoggerProvider, LoggingHandler
from opentelemetry.sdk._logs.export import BatchLogRecordProcessor, SimpleLogRecordProcessor
from opentelemetry.sdk.extension.aws.resource._lambda import (
  AwsLambdaResourceDetector,
)
from opentelemetry.sdk.resources import get_aggregated_resources

logger_provider = LoggerProvider(
    resource=get_aggregated_resources(
          [
              AwsLambdaResourceDetector(),
          ]
      ),
)
set_logger_provider(logger_provider)

exporter = OTLPLogExporter(endpoint='http://0.0.0.0:4318/v1/logs')
logger_provider.add_log_record_processor(BatchLogRecordProcessor(exporter))
handler = LoggingHandler(level=logging.INFO, logger_provider=logger_provider)
# Attach OTLP handler to root logger
logger = logging.getLogger().addHandler(handler)
# Create different namespaced loggers
loggerAgent = logging.getLogger("financeagent.handler")
loggerAgent.setLevel(os.environ['OTEL_LOG_LEVEL'])
### END


## Creates a tracer from the global tracer provider
tracer = trace.get_tracer(__name__)

# Acquire a meter.
meter = metrics.get_meter(__name__)

# Now create a counter instrument to make measurements with
agent_counter = meter.create_counter(
    "agent.calls",
    description="The number of agent calls",
)
get_investment_research_counter = meter.create_counter(
    "get_investment_research.calls",
    description="The number of get_investment_research calls",
)
get_existing_portfolio_counter = meter.create_counter(
    "get_existing_portfolio.calls",
    description="The number of get_existing_portfolio calls",
)


@tracer.start_as_current_span("FinancialAgent_lambda_handler")
def handler(event, context):
    # increment counter
    agent_counter.add(1)
    loggerAgent.debug(f"Received event: {event}")

    # Initialize response code to None
    response_code = None

    # Extract the action group, api path, and parameters from the prediction
    action = event["actionGroup"]
    api_path = event["apiPath"]
    parameters = event["parameters"]
    inputText = event["inputText"]
    httpMethod = event["httpMethod"]

    loggerAgent.debug(f"inputText: {inputText}")

    # Get the query value from the parameters
    query = parameters[0]["value"]
    loggerAgent.debug(f"Query: {query}")

    # Check the api path to determine which tool function to call
    if api_path == "/retrieve_inv_research":
        with tracer.start_as_current_span("FinancialAgent_lambda_handler_get_investment_research") as child:
            get_investment_research_counter.add(1)
            body = tools.get_investment_research(query)
            # Create a response body with the result
            response_body = {"application/json": {"body": str(body)}}
            response_code = 200
    elif api_path == "/retrieve_exist_port":
        with tracer.start_as_current_span("FinancialAgent_lambda_handler_get_existing_portfolio") as child2:
            get_existing_portfolio_counter.add(1)
            body = tools.get_existing_portfolio(query)
            # Create a response body with the result
            response_body = {"application/json": {"body": str(body)}}
            response_code = 200
    else:
        # If the api path is not recognized, return an error message
        body = {"{}::{} is not a valid api, try another one.".format(action, api_path)}
        response_code = 400
        response_body = {"application/json": {"body": str(body)}}

    # Create a dictionary containing the response details
    action_response = {
        "actionGroup": action,
        "apiPath": api_path,
        "httpMethod": httpMethod,
        "httpStatusCode": response_code,
        "responseBody": response_body,
    }

    # Return the list of responses as a dictionary
    api_response = {"messageVersion": "1.0", "response": action_response}
    loggerAgent.debug(f"API response: {api_response}")

    logger_provider.shutdown()
    return api_response
