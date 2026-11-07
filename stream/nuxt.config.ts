import tailwindcss from "@tailwindcss/vite";

// https://nuxt.com/docs/api/configuration/nuxt-config
export default defineNuxtConfig({
  compatibilityDate: "2025-07-15",
  devtools: { enabled: false },
  css: ["~/assets/main.css"],
  vite: {
    plugins: [tailwindcss()]
  },
  runtimeConfig: {
    public: {
      backendUrl: ""
    }
  },
  app: {
    pageTransition: { name: "page", mode: "out-in" },
    layoutTransition: { name: "page", mode: "out-in" },
    head: {
      title: "Pothole Patrol",
      meta: [{ charset: "UTF-8" }, { name: "viewport", content: "width=device-width, initial-scale=1.0" }, { name: "mobile-web-app-capable", content: "yes" }]
    }
  }
});
