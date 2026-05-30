<template>
  <div class="bg-white rounded-xl shadow-sm border border-slate-200 p-5 text-center">
    <div :class="['text-3xl font-bold', colorClass]">{{ value }}</div>
    <div class="text-xs text-slate-500 mt-1 leading-tight">{{ label }}</div>
  </div>
</template>

<script setup>
import { computed } from "vue";

const props = defineProps({
  label: { type: String, required: true },
  value: { type: [String, Number], required: true },
  accent: { type: String, default: "indigo" },
});

const colorClass = computed(() => ({ indigo: "text-indigo-600", emerald: "text-emerald-600", purple: "text-purple-600" })[props.accent] ?? "text-indigo-600");
</script>
