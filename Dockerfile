FROM python:3.9

WORKDIR /app

COPY requirements.txt .

RUN mkdir -p -m 0600 ~/.ssh && ssh-keyscan github.com >> ~/.ssh/known_hosts

RUN --mount=type=ssh pip install -r requirements.txt

COPY . .

ENV CELERY_BROKER_URL=$CELERY_BROKER_URL
ENV CELERY_RESULT_BACKEND=$CELERY_RESULT_BACKEND

#CMD celery -A tasks worker --loglevel=info
#CMD ["/bin/bash"]
