import tools
from opentelemetry import metrics
from opentelemetry import trace
import logging

logging.basicConfig(format='[%(asctime)s] p%(process)s {%(filename)s:%(lineno)d} %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Creates a tracer from the global tracer provider
tracer = trace.get_tracer("appl.tracer")


@tracer.start_as_current_span("lambda_handler")
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
        body = tools.get_investment_research(query)
        # Create a response body with the result
        response_body = {"application/json": {"body": str(body)}}
        response_code = 200
    elif api_path == "/get_existing_portfolio":
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

    return api_response
