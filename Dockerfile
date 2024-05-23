FROM python:3.12-slim

WORKDIR /app

COPY . /app

RUN pip install pipenv
RUN pipenv install --deploy --ignore-pipfile

EXPOSE 6789
CMD ["pipenv", "run", "python", "server.py"]