FROM downloads.unstructured.io/unstructured-io/unstructured:latest

ADD ./api /app

EXPOSE 8000

CMD ["python3", "main.py"]