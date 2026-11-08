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
      title: "Pothole Patrol Camera",
      meta: [
        { charset: "UTF-8" },
        { name: "viewport", content: "width=device-width, initial-scale=1.0" },
        { name: "mobile-web-app-capable", content: "yes" },
        { name: "og:site_name", content: "Pothole Patrol" },
        { name: "og:title", content: "Pothole Patrol Camera" },
        { name: "description", content: "Smarter maintenance starts with seeing the damage. Pothole Patrol helps cities fill the holes that matter!" },
        { name: "og:description", content: "Smarter maintenance starts with seeing the damage. Pothole Patrol helps cities fill the holes that matter!" },
        { name: "og:image", content: "/logo.svg" },
        { name: "og:type", content: "website" }
      ],
      link: [{ rel: "icon", type: "image/svg+xml", href: "/logo-minified.svg" }],
      htmlAttrs: { lang: "en" }
    }
  }
});
