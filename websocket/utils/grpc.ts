import * as protoLoader from "@grpc/proto-loader";
import * as grpc from "@grpc/grpc-js";
import path from "path";

const proto = grpc.loadPackageDefinition(
  protoLoader.loadSync(path.resolve(process.cwd(), "..", "model", "proto", "video.proto"), {
    keepCase: false,
    longs: String,
    enums: String,
    defaults: true,
    oneofs: true
  })
) as grpc.GrpcObject;

const videoPackage = proto.video as grpc.GrpcObject;
const VideoService = videoPackage.VideoService as grpc.ServiceClientConstructor;

const client = new VideoService(process.env.GRPC_SERVER_URL!, grpc.credentials.createInsecure());

export type VideoFrame = {
  data: Buffer;
  timestamp: number;
  latitude: number;
  longitude: number;
  sequence: number;
  streamId: string;
};
export type StreamResponse = {
  framesReceived: string;
};

type VideoClient = grpc.Client & {
  streamFrames: (callback: (error: grpc.ServiceError | null, response: StreamResponse) => void) => grpc.ClientWritableStream<VideoFrame>;
};
// @ts-expect-error
const videoClient = client as VideoClient;

export function createGrpcStream() {
  return videoClient.streamFrames((error, response) => {
    if (error) return console.error("Error receiving stream response:", error);
    console.log("Stream response received:", response.framesReceived);
  });
}
