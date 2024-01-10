import tools
import logging

from opentelemetry import trace


### Explicitly added for logging which is currently in experimental stage and not working with auto-instrumentation
### OTEL_PYTHON_LOGGING_AUTO_INSTRUMENTATION_ENABLED = true
### BEG
from opentelemetry._logs import get_logger
from opentelemetry._logs import set_logger_provider
from opentelemetry.exporter.otlp.proto.http._log_exporter import (
   OTLPLogExporter,
)
from opentelemetry.sdk._logs import LoggerProvider, LoggingHandler
from opentelemetry.sdk._logs.export import BatchLogRecordProcessor
from opentelemetry.sdk.resources import Resource

logger_provider = LoggerProvider(
   resource=Resource.create(
       {
           "service.name": "FinancialAgent"
       }
   ),
)
set_logger_provider(logger_provider)
exporter = OTLPLogExporter()
logger_provider.add_log_record_processor(BatchLogRecordProcessor(exporter))
handler = LoggingHandler(level=logging.NOTSET, logger_provider=logger_provider)
# Attach OTLP handler to root logger
logging.getLogger().addHandler(handler)
logger = logging.getLogger("FinancialAgent")
### END


## Creates a tracer from the global tracer provider
tracer = trace.get_tracer("FinancialAgent")


@tracer.start_as_current_span("FinancialAgent_lambda_handler")
def handler(event, context):
    # Print the received event to the logs
    logger.info("Received event: ")
    logger.info(event)

    # Initialize response code to None
    response_code = None

    # Extract the action group, api path, and parameters from the prediction
    action = event["actionGroup"]
    api_path = event["apiPath"]
    parameters = event["parameters"]
    inputText = event["inputText"]
    httpMethod = event["httpMethod"]

    logger.info(f"inputText: {inputText}")

    # Get the query value from the parameters
    query = parameters[0]["value"]
    logger.info(f"Query: {query}")

    # Check the api path to determine which tool function to call
    if api_path == "/get_investment_research":
        with tracer.start_as_current_span("FinancialAgent_lambda_handler_get_investment_research") as child:
            body = tools.get_investment_research(query)
            # Create a response body with the result
            response_body = {"application/json": {"body": str(body)}}
            response_code = 200
    elif api_path == "/get_existing_portfolio":
        with tracer.start_as_current_span("FinancialAgent_lambda_handler_get_existing_portfolio") as child2:
            body = tools.get_existing_portfolio(query)
            # Create a response body with the result
            response_body = {"application/json": {"body": str(body)}}
            response_code = 200
    else:
        # If the api path is not recognized, return an error message
        body = {"{}::{} is not a valid api, try another one.".format(action, api_path)}
        response_code = 400
        response_body = {"application/json": {"body": str(body)}}

    # Print the response body to the logs
    logger.info(f"Response body: {response_body}")

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
    logger.info(f"API response: {api_response}")

    #logger_provider.shutdown()
    return api_response
