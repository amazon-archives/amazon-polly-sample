# Amazon Polly Sample
This app allows you to easily convert any publicly available RSS content into audio Podcasts, so you can listen to your favorite blogs on mobile devices instead of reading them.

# Requirements
You will need an AWS account and an RSS feed.
Some technical experience is required to setup your own instance of the app, but you don't have to write any code. Once setup, it can be used by anyone using a standard Podcast player.

# How does it work?
1. Amazon CloudWatch periodically triggers a function hosted using AWS Lambda.
2. The function checks for new content on the selected RSS feed.
3. When any new text content is available, it is retrieved, converted into lifelike speech using Amazon Polly, and stored as a set of audio files in a chosen S3 bucket.
4. The same S3 bucket that hosts podcast.xml can be pointed to by any Podcast application (like iTunes), in order to play the audio content.

# Setup
## S3
1. Login to your AWS account.
2. Create a new S3 bucket that will be used to store synthesized audio.
    * Go to the bucket properties->Permissions->Add bucket policy and paste the following policy:
    
        ```
        {
            "Version": "2012-10-17",
            "Statement": [{
                "Sid": "AddPerm",
                "Effect": "Allow",
                "Principal": "*",
                "Action": "s3:GetObject",
                "Resource": "arn:aws:s3:::YOUR_BUCKET_NAME/*"
        }]}
        ```
        Make sure to substitute YOUR_BUCKET_NAME with an arbitrary name, keeping in mind that it has to be globally unique. Save the policy.
    * Expand the "Static Website Hosting" section in the bucket properties, choose "Enable website hosting", type "podcast.xml" in the "Index Document" field, and save the settings.

## Lambda
1. Create a new Lambda function.
2. Choose "Python 2.7" as runtime and "hello-world-python" as a blueprint. 
3. Skip triggerts (just click "Next"); we will get to that later.
4. Choose an arbitrary name for your function, change "Code entry type" to "Upload a .ZIP file", and upload dist/package.zip from this repository.
5. Choose "Create a custom role" in the "Role" field, which will open a new tab.
    * In the newly opened tab, change "IAM Role" to "Create a new IAM Role", and choose an arbitrary name for the role.
    * Expand "View Policy Document", click the "Edit" link, and paste the following content into the text area:
    
        ```
        {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Action": [
                        "polly:SynthesizeSpeech",
                        "s3:ListBucket",
                        "s3:PutObject"
                    ],
                    "Resource": "*"
                }
            ]
        }
        ```
    * Click the "Allow" button at the bottom of the page, which will close the tab and get you back to the Lambda function settings.
6. Change the Timeout to 5 min 0 seconds.
7. Click "Next", review the settings, and click "Create function".
8. Optional check to prove that the new function works as expected:
    * Click "Test" at the top of the page.
    * Use the following JSON document as test even input:
    
        ```
        {
          "rss": "http://feeds.feedburner.com/AmazonWebServicesBlog", 
          "bucket": "YOUR_BUCKET_NAME"
        }
        ```
        Make sure to substitute YOUR_BUCKET_NAME, and feel free to change rss into any RSS URL.
    * Click "Save and test" and wait until the function is finished. Keep in mind that it may take a while to retrieve, convert and store the content.
    * Go back to your newly created S3 bucket to see if it contains any new content.

## CloudWatch
1. Go to Amazon CloudWatch, which will be used to periodically trigger your lambda function.
    * Go to "Events" and click "Create rule".
    * Select "Schedule" in "Event selector".
    * In the "Targets" section, choose "Lambda function", and then choose the newly created function. Expand "Configure input", choose "Constant (JSON text)", use the following JSON document:
    
        ```
        {
          "rss": "http://feeds.feedburner.com/AmazonWebServicesBlog", 
          "bucket": "YOUR_BUCKET_NAME"
        }
        ```
        That's the same JSON that you used before, to test your function (unless you were brave enough to skip that step). Again, make sure to substitute YOUR_BUCKET_NAME and choose your favorite RSS URL.
2. Click configure details.
3. Choose an arbitrary name and click "Create rule".
4. Go back to your S3 bucket, click on the podcast.xml file that was previously created there, and open "Properties".
5. Copy link and use it in any Podcast player (like iTunes or any Podcast app in Android). Optionally, use any URL shortener (like bit.ly) to create a short version of the link.

## Summary
That's it! Your podcast is ready. Use it on your own, or share the URL with your friends. Optionally publish it as an audio version of your own blog (if you are the content owner).

