import boto3

ec2 = boto3.client('ec2', region_name='us-east-1')

def lambda_handler(event, context):
    # Find any running instance in us-east-1
    response = ec2.describe_instances(
        Filters=[
            {'Name': 'instance-state-name', 'Values': ['running']}
        ]
    )
    
    reservations = response.get('Reservations', [])
    if reservations and reservations[0]['Instances']:
        instance_id = reservations[0]['Instances'][0]['InstanceId']
        
        # Terminate the running instance to simulate crash/reset
        ec2.terminate_instances(InstanceIds=[instance_id])
        return {
            'statusCode': 200,
            'body': f'Successfully terminated instance {instance_id}. Auto Scaling Group will self-heal and boot a replacement.'
        }
    
    return {
        'statusCode': 400,
        'body': 'No running instance found.'
    }