<template>
  <div class="flex flex-col items-center justify-center">
    <video v-show="stream" ref="video" autoplay playsinline muted></video>
    <p v-show="!stream" class="text-3xl font-bold">We need camera permissions to continue :(</p>
  </div>
</template>

<script setup lang="ts">
const { $socket } = useNuxtApp();

const FPS = 10;
const QUALITY = 0.75;

const video = useTemplateRef("video");
const stream = ref<MediaStream>();

let frameCallback: number;
onMounted(async () => {
  $socket.connect();

  stream.value = await navigator.mediaDevices.getUserMedia({
    video: { width: 1280, height: 1280, facingMode: "environment" },
    audio: false
  });

  if (!video.value) return;
  video.value.srcObject = stream.value;
  await video.value.play();

  let isEncoding = false;
  let isInFlight = false;
  let lastPolled = -Infinity;

  const canvas = document.createElement("canvas");
  canvas.width = 1280;
  canvas.height = 1280;

  const ctx = canvas.getContext("2d");
  if (!ctx) return;

  frameCallback = video.value.requestVideoFrameCallback((timestamp) => {
    if (timestamp - lastPolled < 1000 / FPS) return;

    if (isEncoding || isInFlight) return;
    if (!$socket.connected) return;
    if (!video.value || video.value.readyState < 2) return;

    let latitude: number;
    let longitude: number;
    if (navigator.geolocation) {
      navigator.geolocation.getCurrentPosition((position) => {
        latitude = position.coords.latitude;
        longitude = position.coords.longitude;
      });
    }

    isEncoding = true;
    lastPolled = timestamp;
    ctx.drawImage(video.value, 0, 0, canvas.width, canvas.height);

    canvas.toBlob(
      (blob) => {
        isEncoding = false;

        if (!blob || !$socket.connected || isInFlight) return;
        isInFlight = true;

        $socket.timeout(2000).emit(
          "sendFrame",
          blob,
          {
            timestamp: Math.floor(Date.now() / 1000),
            latitude: latitude ?? null,
            longitude: longitude ?? null
          },
          (error) => {
            isInFlight = false;
            if (error) console.error("Failed to send frame:", error);
          }
        );
      },
      "image/jpeg",
      QUALITY
    );
  });
});

onBeforeUnmount(() => {
  if (frameCallback) video.value?.cancelVideoFrameCallback(frameCallback);
  $socket.disconnect();
  stream.value?.getTracks().forEach((track) => track.stop());
});
</script>

<style scoped>
@keyframes skeleton {
  0%,
  100% {
    background-color: #303030;
  }
  50% {
    background-color: #404040;
  }
}
.skeleton {
  animation: skeleton 1.5s infinite;
}
</style>
