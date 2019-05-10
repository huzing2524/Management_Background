FROM python:3.6

ENV PG_DATABASE="db_dsd" \
    PG_USER="dsdUser" \
    PG_PASSWORD="dsdUserPassword" \
    PG_HOST="postgres" \
    PG_PORT="5432" \
    RM_HOST="rbtmq" \
    RM_PORT="5672" \
    SETTING_NAME="prod"

RUN mkdir -p /bg
COPY . /bg
WORKDIR /bg
RUN pip install -r requirements.txt
EXPOSE 8000
CMD ["python3", "./management/manage.py", "runserver", "0.0.0.0:8000"]
