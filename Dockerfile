FROM python:3.8-slim-buster

RUN mkdir /code
WORKDIR /code
ADD . /code/
RUN pip install pydicom pynetdicom

CMD ["python", "/code/scp.py"]`