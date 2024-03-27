FROM python:3-alpine

# create app directory
WORKDIR /app

# install app dependencies
COPY requirements.txt ./

RUN pip install -r requirements.txt

# bundle app source
COPY . .

EXPOSE 80

CMD ["flask", "run", "--host=0.0.0.0", "--port=80"]