const dotenv = require("dotenv");
dotenv.config();
var amqp = require("amqplib");
const { spawn } = require("child_process");
const path = require("path");
const fs = require("node:fs/promises");

const RABBITMQ_USERNAME = process.env.RABBITMQ_USERNAME;
const RABBITMQ_PASSWORD = process.env.RABBITMQ_PASSWORD;

const PROCESSING_QUEUE_URL = `amqp://${process.env.REQUESTS_QUEUE_EXTERNAL_URL}:${process.env.REQUESTS_QUEUE_EXTERNAL_PORT}`;
const SUBMITTED_FILE_ROOT = process.env.SUBMITTED_FILE_ROOT;
const OUTPUT_FILE_ROOT = process.env.OUTPUT_FILE_ROOT;
const PROCESSING_SCRIPT_PATH = "/queueService/python/processing.py";
const TARGET_PYTHON_PATH = "/queueService/venv/bin/python";
const OUTPUT_EXTENSION = process.env.OUTPUT_EXTENSION;

const SUBMISSION_QUEUE_NAME = process.env.SUBMISSION_QUEUE_NAME;
const RESULTS_QUEUE_NAME = process.env.RESULTS_QUEUE_NAME;
// create submitted file root directory if it does not exist
fs.mkdir(SUBMITTED_FILE_ROOT, { recursive: true }).catch(console.error);
// create output file root directory if it does not exist
fs.mkdir(OUTPUT_FILE_ROOT, { recursive: true }).catch(console.error);

async function temp_main() {
  await runProcessingScript(5);
}
async function main() {
  let channel;
  let connection;
  try {
    let credentials = amqp.credentials.plain(
      RABBITMQ_USERNAME,
      RABBITMQ_PASSWORD
    );
    connection = await amqp.connect(PROCESSING_QUEUE_URL, {
      credentials: credentials,
      timeout: 100000,
    });

    connection.on("error", (err) => {
      throw err;
    });

    connection.on("close", () => {
      throw new Error("connection closed");
    });
    channel = await connection.createChannel();

    await channel.assertQueue(SUBMISSION_QUEUE_NAME, { durable: true });
    let msg = await channel.get(SUBMISSION_QUEUE_NAME, { noAck: true });
    if (msg === false) {
      return;
    }

    await consumeMessage(msg);
  } catch (error) {
    console.error("Error:", error);
    throw error;
  } finally {
    if (channel) {
      await channel.close();
    }
    if (connection) {
      await connection.close();
    }
  }
}

async function consumeMessage(msg) {
  [file_data, json_data] = await parseMessageContent(msg.content);
  let submission_id = json_data.transcription_id;
  await saveSubmittedFile(file_data, submission_id);
  returnCode = await runProcessingScript(submission_id);

  // if the external program returns 0, send the result to the results queue
  if (returnCode === 0) {
    console.log(
      "External program returned 0, sending result to the results queue"
    );
    await sendResultToQueue(submission_id);
  } else {
    console.error(
      "External program failed, not sending result to the results queue"
    );
  }
}

async function parseMessageContent(msgContent) {
  const dataSize = msgContent.slice(0, 4);
  const binaryDataLength = dataSize.readUInt32BE();
  const binaryData = msgContent.slice(4, 4 + binaryDataLength);
  const json_data = JSON.parse(msgContent.slice(4 + binaryDataLength));
  return [binaryData, json_data];
}

async function runProcessingScript(submission_id) {
  const command = TARGET_PYTHON_PATH;
  const target_file = path.join(SUBMITTED_FILE_ROOT, `${submission_id}`);
  const output_file = path.join(
    OUTPUT_FILE_ROOT,
    `${submission_id}.${OUTPUT_EXTENSION}`
  );
  const args = [PROCESSING_SCRIPT_PATH, target_file, output_file];

  // Spawn the child process
  const childProcess = spawn(command, args);
  childProcess.stdout.on("data", (data) => {
    console.log(`stdout: ${data}`);
  });

  childProcess.stderr.on("data", (data) => {
    console.error(`stderr: ${data}`);
  });
  var promise = new Promise((resolve, reject) => {
    childProcess.on("exit", (code, signal) => {
      console.log(`stdout: ${childProcess.stdout.read()}`);
      // print stderr
      console.error(`stderr: ${childProcess.stderr.read()}`);
      if (signal) {
        console.error(
          `External program terminated due to receipt of signal: ${signal}`
        );
        reject(
          new Error(
            `External program terminated due to receipt of signal: ${signal}`
          )
        );
      } else {
        console.log(`External program exited with code ${code}`);
        resolve(code);
      }
    });

    childProcess.on("error", (error) => {
      console.error("Error:", error);
      reject(error);
    });
  });
  const outputCode = await promise;
  childProcess.kill();
  childProcess.removeAllListeners();
  return outputCode;
}

async function sendResultToQueue(transcription_id) {
  const outputData = await getDataForRequest(transcription_id);
  const message = await formOutputMessage(transcription_id, outputData);
  let connection;
  let channel;
  let connClosed = false;
  try {
    let credentials = amqp.credentials.plain(
      RABBITMQ_USERNAME,
      RABBITMQ_PASSWORD
    );
    connection = await amqp.connect(PROCESSING_QUEUE_URL, {
      credentials: credentials,
      timeout: 100000,
    });

    connection.on("error", (err) => {
      connClosed = true;
      connection.close();
      throw err;
    });

    connection.on("close", () => {
      throw new Error("connection closed");
    });

    channel = await connection.createConfirmChannel();

    channel.on("error", (err) => console.log("Channel error: ", err));
    await channel.assertQueue(RESULTS_QUEUE_NAME, { durable: true });

    let promise = new Promise((resolve, reject) => {
      channel.sendToQueue(
        RESULTS_QUEUE_NAME,
        message,
        { persistent: true },
        (err, ok) => {
          if (err) {
            console.error("Error sending message: ", err);
            reject(err);
          } else {
            resolve();
          }
        }
      );
    });

    await promise;
  } catch (error) {
    console.error("Error:", error);
    throw error;
  } finally {
    if (connection && !connClosed) {
      await connection.close();
    }
  }
}

async function getDataForRequest(transcription_id) {
  output_path = path.join(
    OUTPUT_FILE_ROOT,
    `${transcription_id}.${OUTPUT_EXTENSION}`
  );

  // will throw if the file does not exist
  const data = await fs.readFile(output_path);

  return data;
}

async function formOutputMessage(transcription_id, outputData) {
  const json_data = { transcription_id };

  // create a buffer that contains the size of the binary data
  // that is 4 bytes wide
  const dataSize = Buffer.alloc(4);
  dataSize.writeUInt32BE(outputData.length);
  const json_bin = Buffer.from(JSON.stringify(json_data));

  const message = Buffer.concat([dataSize, outputData, json_bin]);

  return message;
}

async function saveSubmittedFile(file_data, submission_id) {
  const submitted_file_path = path.join(
    SUBMITTED_FILE_ROOT,
    `${submission_id}`
  );
  await fs.writeFile(submitted_file_path, file_data);
}

main();
