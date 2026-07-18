<template>
  <div ref="editorRef" class="json-editor" />
</template>

<script setup lang="ts">
import { ref, onMounted, onBeforeUnmount, watch } from 'vue'
import { EditorState } from '@codemirror/state'
import { EditorView, keymap, lineNumbers, highlightActiveLine } from '@codemirror/view'
import { json } from '@codemirror/lang-json'
import { oneDark } from '@codemirror/theme-one-dark'
import { defaultKeymap, indentWithTab } from '@codemirror/commands'
import { useAppStore } from '@/stores/app'

const props = withDefaults(defineProps<{
  modelValue?: string
  readOnly?: boolean
  height?: string
}>(), {
  modelValue: '{}',
  readOnly: false,
  height: '400px',
})

const emit = defineEmits<{
  'update:modelValue': [value: string]
  'change': [value: string]
}>()

const editorRef = ref<HTMLDivElement>()
const appStore = useAppStore()
let editorView: EditorView | null = null

// 格式化 JSON
function formatJson(str: string): string {
  try {
    return JSON.stringify(JSON.parse(str), null, 2)
  } catch {
    return str
  }
}

onMounted(() => {
  if (!editorRef.value) return

  const formattedValue = formatJson(props.modelValue)
  const updateListener = EditorView.updateListener.of((update) => {
    if (update.docChanged) {
      const val = update.state.doc.toString()
      emit('update:modelValue', val)
      emit('change', val)
    }
  })

  const extensions = [
    lineNumbers(),
    highlightActiveLine(),
    json(),
    keymap.of([...defaultKeymap, indentWithTab]),
    updateListener,
    EditorView.editable.of(!props.readOnly),
    EditorView.theme({ '&': { height: props.height } }),
  ]

  // 根据暗色模式选择主题
  if (appStore.darkMode) {
    extensions.push(oneDark)
  }

  editorView = new EditorView({
    state: EditorState.create({
      doc: formattedValue,
      extensions,
    }),
    parent: editorRef.value,
  })
})

// 监听外部 modelValue 变化（仅在非用户编辑时更新）
watch(() => props.modelValue, (newVal) => {
  if (!editorView) return
  const currentVal = editorView.state.doc.toString()
  if (newVal !== currentVal) {
    editorView.setState(
      EditorState.create({
        doc: formatJson(newVal),
        extensions: editorView.state.facet(EditorView.stateFacet) as any,
      })
    )
  }
})

// 暴露格式化方法
function format() {
  if (!editorView) return
  const current = editorView.state.doc.toString()
  const formatted = formatJson(current)
  editorView.setState(
    EditorState.create({
      doc: formatted,
      extensions: editorView.state.facet(EditorView.stateFacet) as any,
    })
  )
  emit('update:modelValue', formatted)
  emit('change', formatted)
}

defineExpose({ format })

onBeforeUnmount(() => {
  editorView?.destroy()
})
</script>

<style scoped>
.json-editor {
  border: 1px solid var(--el-border-color);
  border-radius: 4px;
  overflow: hidden;
}

.json-editor :deep(.cm-editor) {
  height: 100%;
  font-size: 13px;
}

.json-editor :deep(.cm-scroller) {
  overflow: auto;
}
</style>
