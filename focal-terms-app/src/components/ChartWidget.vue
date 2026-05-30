<template>
  <canvas ref="canvas"></canvas>
</template>

<script setup>
import { ref, onMounted, onUnmounted, watch } from "vue";
import { Chart, registerables } from "chart.js";
Chart.register(...registerables);

const props = defineProps({
  type: { type: String, required: true },
  data: { type: Object, required: true },
  options: { type: Object, default: () => ({}) },
});

const canvas = ref(null);
let chart = null;

function build() {
  if (chart) {
    chart.destroy();
    chart = null;
  }
  if (!canvas.value) return;
  chart = new Chart(canvas.value, {
    type: props.type,
    data: props.data,
    options: { responsive: true, maintainAspectRatio: false, ...props.options },
  });
}

onMounted(build);
watch(() => props.data, build, { deep: true });
onUnmounted(() => {
  if (chart) chart.destroy();
});
</script>
