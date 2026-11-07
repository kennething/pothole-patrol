export default function () {
  const { $socket } = useNuxtApp();

  onMounted(() => {
    if (!$socket.hasListeners("terminatePairing"))
      $socket.on("terminatePairing", () => {
        $socket.disconnect();
        navigateTo("/");
      });
  });
  onBeforeUnmount(() => {
    if ($socket.hasListeners("terminatePairing")) $socket.off("terminatePairing");
  });
}
