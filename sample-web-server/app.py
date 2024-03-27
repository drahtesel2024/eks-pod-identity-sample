# import flask module
from flask import Flask, redirect, url_for

# import the aws module
import boto3

# CHANGE ME initialize a dynamodb client with the appropriate region for where you're deploying your AWS resources
dynamodb = boto3.client('dynamodb', region_name='eu-west-1')

# CHANGE ME to the appropriate table name value
table_name = 'eks-sample-ddb-DDBTable-AZB5FU25DDL8'

# specifies the primary key of the item you want to retrieve
key = {
  'pk': {'S': 'key'}
}

def getItem():
  try:
      response = dynamodb.get_item(
        TableName=table_name,
        Key=key
      )
      if 'Item' in response:
          item = response['Item']
          return item['value']['S']
      else:
          return "item not found in table"
  except Exception as e:
    return "error retrieving item from table"


# initialize flask app
app = Flask(__name__)

@app.route('/')
def index():
  return 'The web server retrieved the following item value from DynamoDB: ' + getItem()
  
@app.route('/favicon.ico')
def favicon():
  return redirect(url_for('static', filename='favicon.ico'))
  
# main driver function
if __name__ == "__main__":
  app.run()