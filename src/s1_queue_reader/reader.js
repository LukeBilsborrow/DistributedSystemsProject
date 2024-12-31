const dotenv = require("dotenv");
dotenv.config();
var amqp = require("amqplib");
const path = require("path");
const fs = require("node:fs/promises");

const SECRET_KEY = process.env.SECRET_KEY;

const RABBITMQ_USERNAME = process.env.RABBITMQ_USERNAME;
const RABBITMQ_PASSWORD = process.env.RABBITMQ_PASSWORD;

const PROCESSING_QUEUE_URL = `amqp://${process.env.REQUESTS_QUEUE_EXTERNAL_URL}:${process.env.REQUESTS_QUEUE_EXTERNAL_PORT}`;

const OUTPUT_EXTENSION = process.env.OUTPUT_EXTENSION;
const PROCESSING_RESPONSE_URL = `http://${process.env.REQUESTS_QUEUE_SUBMISSION_SERVER_EXTERNAL_URL}:${process.env.DJANGO_PORT}/${process.env.REQUESTS_QUEUE_SUBMISSION_SERVER_SUBMISSION_ENDPOINT}`;
const RESULTS_QUEUE_NAME = process.env.RESULTS_QUEUE_NAME;

async function main() {
  let credentials = amqp.credentials.plain(
    RABBITMQ_USERNAME,
    RABBITMQ_PASSWORD
  );
  let connection = await amqp.connect(PROCESSING_QUEUE_URL, {
    credentials: credentials,
    timeout: 100000,
  });

  connection.on("error", (err) => {
    throw err;
  });

  connection.on("close", () => {
    throw new Error("connection closed");
  });

  let channel = await connection.createChannel();
  channel.on("error", (err) => {
    console.log("Channel error: ", err);
    throw err;
  });

  await channel.assertQueue(RESULTS_QUEUE_NAME, { durable: true });

  const queueInfo = await channel.checkQueue(RESULTS_QUEUE_NAME);

  channel.prefetch(1);
  await channel.consume(RESULTS_QUEUE_NAME, async function (msg) {
    try {
      await consumeMessage(msg);
      channel.ack(msg);
    } catch (e) {
      console.error("Problem consuming message: ", e);
      channel.nack(msg);
    }
  });
}

async function consumeMessage(msg) {
  [file_data, json_data] = await parseMessageContent(msg.content);

  let transcription_id = json_data.transcription_id;
  await sendMessageToResultServer(file_data, transcription_id);
}

async function parseMessageContent(msgContent) {
  const dataSize = msgContent.slice(0, 4);
  const binaryDataLength = dataSize.readUInt32BE();
  const binaryData = msgContent.slice(4, 4 + binaryDataLength);
  const json_data = JSON.parse(msgContent.slice(4 + binaryDataLength));
  return [binaryData, json_data];
}

async function sendMessageToResultServer(fileData, transcriptionId) {
  jsonData = {
    status: "success",
    transcription_id: transcriptionId,
  };

  // create multipart form
  const form = new FormData();
  // fileData is a buffer, convert it to a blob
  fileData = new Blob([fileData]);
  form.append("file_data", fileData, {
    filename: "file_data",
  });
  // add all keys in json_data to the form
  for (const key in jsonData) {
    form.append(key, jsonData[key]);
  }

  // create the request object
  const request = new Request(PROCESSING_RESPONSE_URL, {
    method: "POST",
    body: form,
    headers: {
      "x-secret-key": SECRET_KEY,
    },
  });

  // send the request
  const response = await fetch(request);

  // check if the request was successful
  if (!response.ok) {
    throw new Error(`Server responded with status ${response.status}`);
  }
  console.log("Successfully sent message to result server");
}

main();
