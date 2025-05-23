FROM python:3.13.3

RUN pip install psycopg2
RUN pip install "fastapi[standard]"
RUN pip install python-multipart
RUN pip install "python-jose[cryptography]"
RUN pip install "passlib[bcrypt]"
RUN pip install --no-cache-dir fastapi uvicorn
RUN pip install jwt
RUN pip install pyjwt

RUN mkdir app
WORKDIR /app/
COPY . /app
EXPOSE 80
# CMD ["fastapi", "dev", "server.py"]
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "80"]
