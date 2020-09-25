FROM python:3

RUN mkdir /code
WORKDIR /code
ADD . /code/
RUN pip install pydicom pynetdicom

CMD ["python", "/code/scp.py"]`