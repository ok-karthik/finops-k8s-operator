# Simple image for the finops operator
FROM python:3.12-slim
WORKDIR /app

# copy requirements and install
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# copy operator code
COPY operator.py ./

# default command runs operator via kopf
ENTRYPOINT ["kopf", "run", "operator.py"]
