import os
import json
import logging
from dotenv import load_dotenv
from Config.SQS import SQS
from Config.PostgreSQL import PostgresClient
from Validation.AssessmentResponseValidator import Assessment
from Processors.AssessmentGeneration import AssessmentGeneration
from Processors.MaterialsGeneration import MaterialsGeneration
from Data.Repositories.BusinessRepository import BusinessRepository
from Validation.ParseClient import ParseClient, Message, GenerateQuestions

load_dotenv()

logger = logging.getLogger()
logger.setLevel(logging.INFO)

db = None
s3 = None
def get_db():
    """Lazy load database connection"""
    global db
    if db is None:
        db = PostgresClient()
    return db

def handle_message(msg)->bool:
    try:
        client = ParseClient(msg['Body'])
        message = client.parse_body()

        if not message:
            return False
        if not message.get("generate_type"):
            logger.info(f"[INFO] invalid message with not generate_type: {message}")
            return False
        
        business_repository, organization_id = BusinessRepository(db), message.get("organization_id")

        match message.get("generate_type"):
            case "generate_questions":    
                generate_questions = message.get("generate_questions")
                builder = AssessmentGeneration(organization_id, generate_questions, business_repository)
                success = builder.process_question_generation()
                if not success:
                    logger.error("[ERROR] process_question_generation result", success)
                    return False
                
                del builder
                return True
            case "generate_materials":
                generate_materials = message.get("generate_materials")
                builder = MaterialsGeneration(organization_id, generate_materials , business_repository)
                success = builder.process_materials_generation()
                if not success:
                    logger.error("[ERROR] process_materials_generation result", success)
                    return False
                
                del builder
                return True
        return False
    except Exception as e:
        logger.error(f"[ERROR] unable to procecess message {e}")
        return False
        
    

def main():##
    """EC2/Local polling mode"""
    sqs = SQS()
    queue_url = os.getenv("DATA_PROCESS_SQS") 
    if not queue_url:
        raise ValueError("DATA_PROCESS_SQS environment variable not set")
    
    logger.info(f"Starting SQS consumer on queue: {queue_url}")
    # Initialize connections once
    get_db()

    while True:
        try:
            response = sqs.sqs.receive_message(
                QueueUrl=queue_url,
                MaxNumberOfMessages=1,
                WaitTimeSeconds=20,  # Long polling
                VisibilityTimeout=300  # 5 minutes to process
            )
            
            messages = response.get("Messages", [])
            if not messages:
                continue
            
            for msg in messages:
                logger.info(f"[SQS INFO] Processing message: {msg['MessageId']}")
                logger.info(f"[SQS INFO] Processing message: {msg['Body']}")
                success = handle_message(msg)
                if success:
                    # Delete message from queue
                    sqs.delete_sqs_message(msg['ReceiptHandle'])
                    logger.info(f"[SQS INFO] Message deleted: {msg['MessageId']}")
                else:
                    # Message will become visible again after visibility timeout
                    logger.warning(f"[SQS] Message processing failed, will retry: {msg['MessageId']}")
                    
        except KeyboardInterrupt:
            logger.info("[SQS ERROR] Shutting down gracefully...")
            break
        except Exception as e:
            logger.error(f" [SQS ERROR] Error in main loop: {e}", exc_info=True)
            # Continue processing next messages
   


def lambda_handler(event, context):
    """
    AWS Lambda entry point.
    
    Lambda automatically:
    - Polls SQS
    - Invokes this function with batches of messages
    - Deletes messages if function succeeds (no exception)
    - Retries messages if function fails (exception raised)
    """
    logger.info(f"Lambda invoked with {len(event['Records'])} messages")
    
    # Initialize connections (reused across warm starts) 
    get_db()
    
    processed = 0
    failed = 0
    
    for record in event['Records']:
        try:
            # Format message to match handle_message expectations
            msg = {
                'Body': record['body'],
                'ReceiptHandle': record['receiptHandle'],
                'MessageId': record['messageId']
            }
            success = handle_message(msg)
            if success:
                processed += 1
            else:
                failed += 1
                # Don't raise exception - let Lambda retry individual messages
                
        except Exception as e:
            logger.error(f"Error processing record {record['messageId']}: {e}", exc_info=True)
            failed += 1
    
    logger.info(f"Batch complete: {processed} processed, {failed} failed")
    
    # If any messages failed, raise exception to trigger Lambda retry
    if failed > 0:
        raise Exception(f"{failed} messages failed processing")
    
    return {
        "statusCode": 200,
        "body": json.dumps({
            "processed": processed,
            "failed": failed
        })
    }

def is_valid():
    try:
        with open("./Validation/assessment_test_payload.json") as file:
            body = json.load(file)
            mock_assessment = Assessment(**body)
            logger.info(f"[INFO] mock_assessment _ {mock_assessment}")
    except Exception as e:
        logger.error(f"[ERROR] unable to load file {e}")


if __name__ == "__main__":
    if os.getenv("APP_MODE") == "prod":
        logger.info("Running on lambda mode - waiting for invocations")
    else:
        logger.info("[INFO] Running in polling mode")
        ## is_valid()
        main()