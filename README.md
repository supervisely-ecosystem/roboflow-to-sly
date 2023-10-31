<div align="center" markdown>
<img src="https://github-production-user-asset-6210df.s3.amazonaws.com/118521851/279346587-26e4d400-9fe7-45e9-a711-9663b1f88565.png"/>

# Convert and copy multiple Roboflow projects into Supervisely at once

<p align="center">
  <a href="#Overview">Overview</a> •
  <a href="#Preparation">Preparation</a> •
  <a href="#How-To-Run">How To Run</a>
</p>

[![](https://img.shields.io/badge/supervisely-ecosystem-brightgreen)](https://ecosystem.supervise.ly/apps/supervisely-ecosystem/roboflow-to-sly)
[![](https://img.shields.io/badge/slack-chat-green.svg?logo=slack)](https://supervise.ly/slack)
![GitHub release (latest SemVer)](https://img.shields.io/github/v/release/supervisely-ecosystem/roboflow-to-sly)
[![views](https://app.supervise.ly/img/badges/views/supervisely-ecosystem/roboflow-to-sly.png)](https://supervise.ly)
[![runs](https://app.supervise.ly/img/badges/runs/supervisely-ecosystem/roboflow-to-sly.png)](https://supervise.ly)

</div>

## Overview

This application allows you to copy multiple projects from Roboflow instance to Supervisely instance, you can select which projects should be copied, labels and tags will be converted automatically. You can preview the results in the table, which will show URLs to corresdponding projects in Roboflow and Supervisely.<br>

## Preparation

ℹ️ NOTE: Every project in Roboflow MUST contain at least one version, otherwise it's impossible to export data from Roboflow. Learn more about Versions in [Roboflow documentation](https://docs.roboflow.com/datasets/create-a-dataset-version).

In order to run the app, you need to obtain `Private API key` to work with Roboflow API. You can refer to [this documentation](https://docs.roboflow.com/api-reference/authentication) to do it.

The API key should looks like this: `qASymt32UTnQV1qABszF`

Now you have two options to use your API key: you can use team files to store an .env file with or you can enter the API key directly in the app GUI. Using team files is recommended as it is more convenient and faster, but you can choose the option that is more suitable for you.

### Using team files

You can download an example of the .env file [here](https://github.com/supervisely-ecosystem/roboflow-to-sly/files/13214150/roboflow.env.zip) and edit it without any additional software in any text editor.<br>
NOTE: you need to unzip the file before using it.<br>

1. Create a .env file with the following content:
   `ROBOFLOW_API_KEY="qASymt32UTnQV1qABszF"`
2. Upload the .env file to the team files.
3. Right-click on the .env file, select `Run app` and choose the `Roboflow to Supervisely Migration Tool` app.

The app will be launched with the API key from the .env file and you won't need to enter it manually.
If everything was done correctly, you will see the following message in the app UI:

- ℹ️ Connection settings was loaded from .env file.
- ✅ Successfully connected to `https://api.roboflow.com`.

### Entering credentials manually

1. Launch the app from the Ecosystem.
2. Enter the API key.
3. Press the `Connect to Roboflow` button.

![credentials](https://github-production-user-asset-6210df.s3.amazonaws.com/118521851/279336687-6dd0bf2c-cbec-49f0-b44f-d7f130d53448.png)

If everything was done correctly, you will see the following message in the app UI:

- ✅ Successfully connected to `https://api.roboflow.com`.<br>

NOTE: The app will not save your API key, you will need to enter them every time you launch the app. To save your time you can use the team files to store your credentials.

## How To Run

NOTE: In this section, we consider that you have already connected to Roboflow instance and have the necessary permissions to work with them. If you haven't done it yet, please refer to the [Preparation](#Preparation) section.<br>
So, here is the step-by-step guide on how to use the app:

**Step 1:** Select projects to copy<br>
After connecting to the Roboflow instance, list of the projects will be loaded into the widget automatically. You can select which projects you want to copy to Supervisely and then press the `Select projects` button.<br>

![select_projects](https://github-production-user-asset-6210df.s3.amazonaws.com/118521851/279336708-464f6968-1b8f-4aea-a9a3-dedb3e30d9d1.png)

**Step 2:** Take a look on list of projects<br>
After completing the `Step 1️⃣`, the application will retrieve information about the projects from roboflow API and show it in the table. Here you can find the links to the projects in Roboflow, and after copying the projects to Supervisely, links to the projects in Supervisely will be added to the table too.<br>

![projects_table](https://github-production-user-asset-6210df.s3.amazonaws.com/118521851/279336714-ed971b00-74dd-482e-9215-862f903c3d8d.png)<br>

**Step 3:** Press the `Copy` button<br>
Now you only need to press the `Copy` button and wait until the copying process is finished. You will see the statuses of the copying process for each project in the table. If any errors occur during the copying process, you will see the error status in the table. When the process is finished, you will see the total number of successfully copied projects and the total number of projects that failed to copy.<br>

![copy_projects](https://github-production-user-asset-6210df.s3.amazonaws.com/118521851/279336719-3b04793a-7526-4bf4-aea0-1dacf71c68d2.png)<br>

![finished](https://github-production-user-asset-6210df.s3.amazonaws.com/118521851/279336726-5a6464d2-d2d0-4e1a-8866-135a23cbc051.png)<br>

The application will be stopped automatically after the copying process is finished.<br>

ℹ️ The app supports following Roboflow project types:
- Object Detection
- Classification
- Instance Segmentation

## Acknowledgement

- [Roboflow Python GitHub](https://github.com/roboflow/roboflow-python) ![GitHub Org's stars](https://img.shields.io/github/stars/roboflow/roboflow-python?style=social)
- [Roboflow Documentation](https://docs.roboflow.com/)
