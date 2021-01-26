FROM python:3.9-slim-buster

ARG USER_ID
ARG GROUP_ID

RUN addgroup --gid $GROUP_ID user
RUN adduser --disabled-password --gecos '' --uid $USER_ID --gid $GROUP_ID user

USER user

RUN mkdir /code
WORKDIR /code
ADD . /code/
RUN pip install pydicom pynetdicom

CMD ["python", "/code/scp_scu.py"]
