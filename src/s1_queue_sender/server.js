express = require("express");
multer = require("multer");
require("dotenv").config();
const { handleSubmit } = require("./server_utils");
const app = express();
const PORT = process.env.REQUESTS_QUEUE_SUBMISSION_SERVER_EXTERNAL_PORT;
const SUBMIT_ENDPOINT =
  process.env.REQUESTS_QUEUE_SUBMISSION_SERVER_SUBMISSION_ENDPOINT;

const storage = multer.memoryStorage();

const upload = multer({ storage: storage });

app.post(`/${SUBMIT_ENDPOINT}`, upload.any(), async (req, res) => {
  await handleSubmit(req, res);
});

app.listen(PORT, () => {
  console.log(`listening at http://localhost:${PORT}`);
});
