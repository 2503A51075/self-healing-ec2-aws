# self-healing-ec2-aws
Autonomous AWS EC2 self-healing prototype using S3, API Gateway, Lambda, and Auto Scaling.
# ☁️ Self-Healing EC2 on AWS

A software-only prototype that demonstrates **automatic infrastructure recovery** on AWS. A web dashboard sends a "failure" signal through API Gateway to a Lambda function, which terminates the running EC2 instance. An Auto Scaling Group notices the missing capacity and launches a replacement instance automatically, with no manual action.

**Region:** `us-east-1` (N. Virginia) · **Environment:** AWS Academy Learner Lab

---

## 📌 Contents

1. [Architecture](#-architecture)
2. [How It Works](#-how-it-works)
3. [Tech Stack](#-tech-stack)
4. [Repository Structure](#-repository-structure)
5. [AWS Setup Guide](#-aws-setup-guide)
6. [Running the Demo](#-running-the-demo)
7. [Screenshots](#-screenshots)
8. [Troubleshooting](#-troubleshooting)
9. [Cleanup](#-cleanup)
10. [Known Limitations](#-known-limitations)
11. [Future Improvements](#-future-improvements)

---

## 🏗 Architecture

```text
┌──────────────────────┐
│  Dashboard (S3)      │   index.html (dash2.html)
│  Static website      │
└──────────┬───────────┘
           │  HTTP GET
           ▼
┌──────────────────────┐
│  Amazon API Gateway  │   HTTP API
└──────────┬───────────┘
           │  invokes
           ▼
┌──────────────────────┐
│  AWS Lambda          │   Python 3.12 + boto3
│  SelfHealing_Reset_  │   terminate_instances()
│  Trigger             │
└──────────┬───────────┘
           │  terminates the running instance
           ▼
┌──────────────────────┐
│  Amazon EC2          │   t2.micro
└──────────┬───────────┘
           │  capacity drops from 1 to 0
           ▼
┌──────────────────────┐
│  Auto Scaling Group  │   SelfHealing-ASG
│  launches replacement│   uses SelfHealing-EC2-Template
└──────────┬───────────┘
           ▼
┌──────────────────────┐
│  Amazon CloudWatch   │   metrics & health monitoring
└──────────────────────┘
```

---

## ⚙️ How It Works

| Step | Phase | What happens |
|------|-------|--------------|
| 1 | **Reset Triggered** | Clicking *Simulate EC2 Failure* on the dashboard calls the API Gateway endpoint. |
| 2 | **EC2 Terminated** | API Gateway invokes the Lambda function, which finds a running instance in `us-east-1` and terminates it. |
| 3 | **Replacement Launch** | The Auto Scaling Group sees the instance count is below the desired capacity and launches a new `t2.micro` from the launch template. |
| 4 | **Service Recovered** | The new instance passes its status checks and the group is back to its healthy state (1 / 1). |

Typical recovery time is about **60 seconds**.

---

## 🧰 Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | HTML, CSS, JavaScript |
| Hosting | Amazon S3 static website hosting |
| API | Amazon API Gateway (HTTP API) |
| Backend | AWS Lambda, Python 3.12, `boto3` |
| Compute | Amazon EC2 (Amazon Linux 2023, `t2.micro`) |
| Recovery | EC2 Auto Scaling Group + Launch Template |
| Monitoring | Amazon CloudWatch |

---

## 📂 Repository Structure

```text
self-healing-ec2-aws/
├── README.md
│── dash2.html             # Dashboard (uploaded to S3 as index.html)
│── lambda_function.py     # Lambda code that terminates the running instance
└── screenshots/           
```

---

## 🚀 AWS Setup Guide

Follow the steps **in order**. Everything is created in **us-east-1**. Check the region in the top-right of the AWS Console before each step.

### Resources you will create

| # | Resource | Name |
|---|----------|------|
| 1 | EC2 Launch Template | `SelfHealing-EC2-Template` |
| 2 | Auto Scaling Group | `SelfHealing-ASG` |
| 3 | Lambda Function | `SelfHealing_Reset_Trigger` |
| 4 | API Gateway (HTTP API) | created from the Lambda trigger |
| 5 | S3 Bucket | `selfhealing-dashboard-2026` (must be globally unique, so change it if taken) |

---

### Step 1: Create the Launch Template

The launch template tells the Auto Scaling Group what kind of instance to start.

1. In the AWS Console search bar, type **EC2** and open it.
2. In the left sidebar, click **Launch Templates**, then **Create launch template**.
3. **Launch template name:** `SelfHealing-EC2-Template`
4. **AMI:** *Amazon Linux 2023 AMI* (Quick Start).
5. **Instance type:** `t2.micro` (or `t3.micro`).
6. **Key pair:** select `vockey`.
7. **Security group:** select the default security group, or one that allows **SSH (22)** and **HTTP (80)**.
8. Expand **Advanced details** and set **IAM instance profile** to `LabInstanceProfile`.
9. *(Optional)* Under **Resource tags**, add Key `Name`, Value `project2` (or any name), Resource type **Instances**. Replacement instances will then be named automatically.
10. Click **Create launch template**.

✅ **Check:** `SelfHealing-EC2-Template` appears in the table with Default version **1**.

---

### Step 2: Create the Auto Scaling Group

1. In the EC2 sidebar, click **Auto Scaling Groups**, then **Create Auto Scaling group**.
2. **Name:** `SelfHealing-ASG`
3. **Launch template:** select `SelfHealing-EC2-Template` and click **Next**.
4. **Network:** choose the default VPC and select at least one subnet (for example `us-east-1a`). Click **Next**.
5. Leave load balancing and health check options at their defaults (EC2 health checks) and click **Next**.
6. **Group size:** set **Desired capacity = 1**, **Minimum = 1**, **Maximum = 1**.
7. Click **Skip to review**, then **Create Auto Scaling group**.

✅ **Check:** Within about 60 seconds, **EC2 → Instances** shows a new instance in **Running** state with **2/2 checks passed**.

---

### Step 3: Create the Lambda Function

1. In the search bar, type **Lambda** and open it.
2. Click **Create function** → **Author from scratch**.
3. **Function name:** `SelfHealing_Reset_Trigger`
4. **Runtime:** Python 3.12
5. Expand **Change default execution role** → **Use an existing role** → select **LabRole**.
6. Click **Create function**.
7. In the **Code** tab, replace the contents of `lambda_function.py` with the code below, then click **Deploy**.

```python
import boto3

ec2 = boto3.client('ec2', region_name='us-east-1')


def lambda_handler(event, context):
    # Find a running instance in us-east-1
    response = ec2.describe_instances(
        Filters=[
            {'Name': 'instance-state-name', 'Values': ['running']}
        ]
    )

    reservations = response.get('Reservations', [])
    if reservations and reservations[0]['Instances']:
        instance_id = reservations[0]['Instances'][0]['InstanceId']

        # Terminate the instance to simulate a crash
        ec2.terminate_instances(InstanceIds=[instance_id])
        return {
            'statusCode': 200,
            'body': f'Successfully terminated instance {instance_id}. '
                    'Auto Scaling Group will launch a replacement.'
        }

    return {
        'statusCode': 400,
        'body': 'No running instance found.'
    }
```

> ⚠️ This function terminates the **first running instance in the region**. Make sure the only running instance in your account is the one launched by `SelfHealing-ASG`, or see [Future Improvements](#-future-improvements) for tag filtering.

✅ **Check:** The Deploy banner shows *Successfully updated the function*.

---

### Step 4: Add the API Gateway Trigger

1. On the Lambda function page, click **Add trigger**.
2. Select **API Gateway**.
3. Choose **Create a new API**, type **HTTP API**, security **Open**.
4. Click **Add**.
5. Open **Configuration → Triggers** and copy the **API endpoint** URL. It looks like:
   `https://<api-id>.execute-api.us-east-1.amazonaws.com/default/SelfHealing_Reset_Trigger`

✅ **Check:** Opening the URL in a browser triggers the Lambda and returns a JSON message. **This terminates the running instance**, so only do it when you want to test the reset.

---

### Step 5: Configure the Dashboard

1. Open `/dash2.html` in a text editor.
2. Find the input with `id="api"` and set its `value` to **your** API endpoint URL from Step 4:

```html
<input id="api" value="https://<api-id>.execute-api.us-east-1.amazonaws.com/default/SelfHealing_Reset_Trigger">
```

3. Rename the file to `index.html` before uploading.

---

### Step 6: Host the Dashboard on S3

1. In the search bar, type **S3** and open it.
2. Click **Create bucket**.
   - **Bucket name:** `selfhealing-dashboard-2026` (or another unique name)
   - **Region:** US East (N. Virginia) `us-east-1`
   - **Object Ownership:** keep ACLs disabled
   - **Block Public Access:** uncheck **Block all public access** and tick the acknowledgment box
3. Click **Create bucket**.
4. Open the bucket → **Upload** → **Add files** → select `index.html` → **Upload**.
5. Go to the **Properties** tab → scroll to **Static website hosting** → **Edit**:
   - Select **Enable**
   - Hosting type: **Host a static website**
   - Index document: `index.html`
   - Click **Save changes**
6. Go to the **Permissions** tab → **Bucket policy** → **Edit**, paste the policy below (replace `YOUR-BUCKET-NAME`), and click **Save changes**:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "PublicReadGetObject",
      "Effect": "Allow",
      "Principal": "*",
      "Action": "s3:GetObject",
      "Resource": "arn:aws:s3:::YOUR-BUCKET-NAME/*"
    }
  ]
}
```

7. Return to **Properties → Static website hosting** and copy the **Bucket website endpoint**, for example:
   `http://selfhealing-dashboard-2026.s3-website-us-east-1.amazonaws.com`

✅ **Check:** Opening the endpoint in a browser shows the **SelfHealing EC2 Operations** dashboard with status **HEALTHY** and capacity **1 / 1**.

---

## ▶️ Running the Demo

1. In **EC2 → Instances**, confirm one instance is **Running**.
2. Open the S3 website endpoint. The dashboard should show **HEALTHY (1 / 1)**.
3. Click **🔥 Simulate EC2 Failure / Trigger Reset**.
4. Watch the dashboard move through the four phases (Reset Triggered → EC2 Terminated → Replacement Launch → Service Recovered) while the activity log updates.
5. Switch to **EC2 → Instances**, remove the *Instance state = running* filter, and refresh. You should see the old instance **Terminated** and a new instance **Running** (status checks 2/2 after about a minute).

You can also test the backend alone: open the Lambda function and click **Test** with an empty event `{}`. The result should show `statusCode: 200`.

---

## 🖼 Screenshots

| Figure | Description | File |
|--------|-------------|------|
| 1 | EC2 Launch Template (`SelfHealing-EC2-Template`, default version) | `screenshots/fig1-launch-template.png` |
| 2 | Auto Scaling Group (desired / min / max = 1) | `screenshots/fig2-asg.png` |
| 3 | Running EC2 instance launched by the ASG | `screenshots/fig3-ec2-running.png` |
| 4 | Lambda function configuration and code | `screenshots/fig4-lambda-config.png` |
| 5 | Lambda test execution result | `screenshots/fig5-lambda-result.png` |
| 6 | API Gateway trigger | `screenshots/fig6-api-gateway.png` |
| 7 | Dashboard before reset | `screenshots/fig7-dashboard-before.png` |
| 8 | Dashboard during reset (recovery animation and logs) | `screenshots/fig8-dashboard-during.png` |
| 9 | Old instance terminated, replacement running | `screenshots/fig9-ec2-replacement.png` |

To show an image in this README:

```markdown
![Figure 1 - Launch Template](screenshots/fig1-launch-template.png)
```

---

## 🛠 Troubleshooting

| Problem | Likely cause | Fix |
|---------|-------------|-----|
| No instance appears after creating the ASG | Wrong subnet or launch template error | Open the ASG → **Activity** tab and read the failure message. |
| Lambda returns `AccessDenied` | Wrong execution role | Set the role to `LabRole` under **Configuration → Permissions**. |
| Lambda returns `No running instance found` | The instance is still starting or already terminated | Wait until the instance shows **Running**, then retry. |
| Dashboard shows 403 Forbidden | Bucket policy missing or public access still blocked | Re-check Step 6, points 2 and 6. |
| Dashboard shows 404 | File not named `index.html` | Rename and re-upload the file, and confirm the index document setting. |
| Button works but nothing is terminated | Wrong API URL in the dashboard | Re-copy the Invoke URL from the Lambda trigger into `index.html` and re-upload. |
| Replacement instance has no name | Launch template has no `Name` tag | Add the tag in Step 1, point 9, and set the new version as default. |

---

## 🧹 Cleanup

The Learner Lab budget is limited, so remove billable resources after you finish:

1. **Delete `SelfHealing-ASG` first** (EC2 → Auto Scaling Groups → Delete). Otherwise it keeps launching instances. Deleting it also terminates its instance.
2. In **EC2 → Instances**, confirm nothing is **Running** or **Pending**.
3. In **EC2 → Volumes**, delete any unattached (*Available*) volumes.
4. The launch template, Lambda function, API Gateway and S3 bucket cost almost nothing when idle. Delete them too if you want a clean account.

> ⚠️ Do not click **Reset** in the Learner Lab panel unless you want every resource wiped.

---

## ⚠️ Known Limitations

- The Lambda terminates the **first running instance in `us-east-1`**, not only this project's instance.
- The dashboard's recovery animation is **timer-based** (about 60 seconds). It does not read real instance state from AWS. The request uses `mode: "no-cors"`, so the page cannot read the Lambda response.
- The API endpoint has **no authentication**, which is fine for a short lab demo but not for production.

---

## 🔮 Future Improvements

- Filter the Lambda by tag (for example `AutoHeal=true`) so it only terminates intended instances.
- Add a second Lambda endpoint that returns real instance and ASG status so the dashboard shows live data.
- Secure the API with an API key or IAM authorization.
- Add a CloudWatch alarm with SNS email notification when a replacement is launched.
- Define the stack as code with CloudFormation or Terraform.
- Add the original hardware idea: an ESP32 button publishing through AWS IoT Core to trigger the reset.

---

## 🔒 Security Note

Never commit AWS access keys or secret keys. The API Gateway URL can be replaced with a placeholder such as `YOUR_API_GATEWAY_ENDPOINT_URL` before publishing the repository.
