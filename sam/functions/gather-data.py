from mychevy.mychevy import MyChevy
import datetime
import json
import boto3
import tempfile
import os


def lambda_handler(event, context):
  now = datetime.datetime.now().isoformat()

  ssm = boto3.client('ssm')
  rawparams = ssm.get_parameters_by_path(
    Path=os.environ['SSMPATHROOT'],
    Recursive=True,
    WithDecryption=True
  )

  params = {}

  for param in rawparams.get('Parameters'):
    params[os.path.basename(param['Name'])] = param['Value']

  if ("user" not in params) or ("password" not in params):
    print("Error: Credential Parameters Not Present")
    raise "Credential Parameters not Present at " + os.environ['SSMPATHROOT']

  page = MyChevy(params['user'], params['password'])
  # This takes up to 2 minutes to return, be patient

  # build credentials and starts a session on the mychevy site
  page.login()

  # gets a list of cars associated with your account
  page.get_cars()

  # update stats for all cars, and returns the list of cars. This will take
  # 60+ seconds per car
  cars = page.update_cars()
  s3 = boto3.client('s3')
  ts = datetime.datetime.now()

  for car in cars:
    tmpf2 = tempfile.NamedTemporaryFile(delete=False)

    cardoc = {
      "time": ts.isoformat().replace('T', ' '),
      "name": car.name,
      "onstar": car.onstar,
      "vin": car.vin,
      "range": car.electricRange,
      "totalRange": car.totalRange,
      "batteryLevel": car.batteryLevel,
      "electricMiles": car.electricMiles,
      "pluggedIn": car.plugged_in,
      "totalMiles": car.totalMiles,
      "chargeState": car.chargeState,
      "chargeMode": car.chargeMode,
      "voltage": car.voltage,
      "estimatedFullChargeBy": car.estimatedFullChargeBy
    }

    if ("DATA_BUCKET" in os.environ):
      with open(tmpf2.name, 'w') as outfile:
        json.dump(cardoc, outfile)
      s3.upload_file(tmpf2.name, os.environ["DATA_BUCKET"], "datafile-" + ts.isoformat())
    else:
      print(car)
      print(cardoc)