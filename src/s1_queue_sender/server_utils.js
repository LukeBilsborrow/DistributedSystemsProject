const amqp = require("amqplib");
require("dotenv").config();

const SUBMISSION_QUEUE_NAME = process.env.SUBMISSION_QUEUE_NAME;
const REQUESTS_QUEUE_URL = `amqp://${process.env.REQUESTS_QUEUE_EXTERNAL_URL}:${process.env.REQUESTS_QUEUE_EXTERNAL_PORT}`;
const RABBITMQ_USERNAME = process.env.RABBITMQ_USERNAME;
const RABBITMQ_PASSWORD = process.env.RABBITMQ_PASSWORD;
const SECRET_KEY = process.env.SECRET_KEY;

async function handleSubmit(req, res) {
  try {
    await checkSecret(req);
    let reqData = await getRequiredFields(req);
    await sendToQueue(reqData);
    res.status(200).send("Data submitted");
  } catch (error) {
    res.status(500).send("Error submitting data");
  }
}

async function checkSecret(req) {
  let secret = req.headers["x-secret-key"];

  if (secret !== SECRET_KEY) {
    throw new Error("Invalid secret");
  }
  console.log("Secret key is valid");
}

async function getRequiredFields(req) {
  let file_data = req.files[0];
  let transcription_id = req.body.transcription_id;
  let status = req.body.status;
  return { file_data, transcription_id, status };
}

async function sendToQueue(data) {
  // send data to queue
  const message = await buildQueueMessage(data);

  let connection;
  let channel;
  try {
    let credentials = amqp.credentials.plain(
      RABBITMQ_USERNAME,
      RABBITMQ_PASSWORD
    );
    connection = await amqp.connect(REQUESTS_QUEUE_URL, { credentials });

    connection.on("error", (err) => {
      throw err;
    });

    connection.on("close", () => {
      throw new Error("connection closed");
    });

    channel = await connection.createChannel();

    // Declare the queue
    await channel.assertQueue(SUBMISSION_QUEUE_NAME, { durable: true });

    channel.sendToQueue(SUBMISSION_QUEUE_NAME, message, { persistent: true });
  } catch (error) {
    console.error("Error:", error);
    throw error;
  } finally {
    // assumes that the connection and channel are always created
    // but this may not be the case if an error occurs
    await channel.close();
    await connection.close();
  }
}

async function buildQueueMessage(data) {
  // create new object which has all keys from data
  // apart from "file"
  let fileData = data.file_data;

  // extract the other fields to a new object
  let messageJson = { transcription_id: data["transcription_id"] };

  const filesizeBin = Buffer.alloc(4);
  filesizeBin.writeUInt32BE(fileData.buffer.length);

  const jsonBin = Buffer.from(JSON.stringify(messageJson));
  // log the size of the JSON data

  const message = Buffer.concat([filesizeBin, fileData.buffer, jsonBin]);

  return message;
}

module.exports = {
  handleSubmit,
};
