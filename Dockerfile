# Dockerfile.lambda
FROM public.ecr.aws/lambda/python:3.11

# Install dependencies
WORKDIR ${LAMBDA_TASK_ROOT}

RUN pip install --upgrade pip
# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Set Lambda handler
CMD [ "main.lambda_handler" ]