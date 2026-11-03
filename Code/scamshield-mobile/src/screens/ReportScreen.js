import { useState, useCallback } from 'react'
import {
  View,
  Text,
  TextInput,
  Pressable,
  StyleSheet,
  ScrollView,
  KeyboardAvoidingView,
  Platform,
  ActivityIndicator,
} from 'react-native'
import { submitReport, ApiError } from '../api'
import { getDeviceId } from '../deviceId'
import { addToHistory } from '../history'
import RiskResultCard from '../components/RiskResultCard'
import { colors, spacing, radius, typography } from '../theme'

export default function ReportScreen() {
  const [number, setNumber] = useState('')
  const [message, setMessage] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [result, setResult] = useState(null)
  const [error, setError] = useState(null)

  const canSubmit = number.trim().length > 0 && message.trim().length > 0 && !submitting

  const handleSubmit = useCallback(async () => {
    setSubmitting(true)
    setError(null)
    setResult(null)
    try {
      const deviceId = await getDeviceId()
      const response = await submitReport(deviceId, number.trim(), message.trim())
      setResult(response)
      await addToHistory({
        number: response.number,
        message: message.trim(),
        score: response.message_score,
        status: response.status,
        submittedAt: new Date().toISOString(),
      })
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Something went wrong submitting this report.')
    } finally {
      setSubmitting(false)
    }
  }, [number, message])

  const handleReset = () => {
    setNumber('')
    setMessage('')
    setResult(null)
    setError(null)
  }

  return (
    <KeyboardAvoidingView style={styles.flex} behavior={Platform.OS === 'ios' ? 'padding' : undefined}>
      <ScrollView contentContainerStyle={styles.content} keyboardShouldPersistTaps="handled">
        <Text style={styles.helperText}>
          Received a suspicious text? Paste the sender's number and the message below.
        </Text>

        <Text style={styles.fieldLabel}>Sender's number</Text>
        <TextInput
          style={styles.input}
          value={number}
          onChangeText={setNumber}
          placeholder="e.g. +260 97X XXX XXX"
          placeholderTextColor={colors.textMuted}
          keyboardType="phone-pad"
          editable={!submitting}
        />

        <Text style={styles.fieldLabel}>Message content</Text>
        <TextInput
          style={[styles.input, styles.textArea]}
          value={message}
          onChangeText={setMessage}
          placeholder="Paste the full text of the message here"
          placeholderTextColor={colors.textMuted}
          multiline
          numberOfLines={5}
          editable={!submitting}
        />

        {error && (
          <View style={styles.errorBanner}>
            <Text style={styles.errorText}>{error}</Text>
          </View>
        )}

        <Pressable
          style={[styles.submitButton, !canSubmit && styles.submitButtonDisabled]}
          onPress={handleSubmit}
          disabled={!canSubmit}
        >
          {submitting ? (
            <ActivityIndicator color="#FFFFFF" />
          ) : (
            <Text style={styles.submitLabel}>Submit report</Text>
          )}
        </Pressable>

        <RiskResultCard result={result} />

        {result && (
          <Pressable style={styles.resetLink} onPress={handleReset}>
            <Text style={styles.resetLinkText}>Report another message</Text>
          </Pressable>
        )}
      </ScrollView>
    </KeyboardAvoidingView>
  )
}

const styles = StyleSheet.create({
  flex: { flex: 1 },
  content: { padding: spacing.lg, paddingBottom: spacing.xl * 2 },
  helperText: { ...typography.body, color: colors.textSecondary, marginBottom: spacing.md, lineHeight: 20 },
  fieldLabel: {
    ...typography.label,
    color: colors.textMuted,
    marginBottom: spacing.xs,
    marginTop: spacing.sm,
  },
  input: {
    backgroundColor: colors.surface,
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: radius.md,
    paddingHorizontal: spacing.md,
    paddingVertical: 10,
    fontSize: 14,
    color: colors.textPrimary,
  },
  textArea: { minHeight: 110, textAlignVertical: 'top' },
  errorBanner: {
    backgroundColor: colors.dangerMuted,
    borderRadius: radius.md,
    padding: spacing.md,
    marginTop: spacing.md,
  },
  errorText: { color: colors.danger, fontSize: 13 },
  submitButton: {
    backgroundColor: colors.primary,
    borderRadius: radius.md,
    paddingVertical: 14,
    alignItems: 'center',
    marginTop: spacing.lg,
  },
  submitButtonDisabled: { backgroundColor: colors.textMuted },
  submitLabel: { color: '#FFFFFF', fontSize: 15, fontWeight: '600' },
  resetLink: { alignItems: 'center', marginTop: spacing.md },
  resetLinkText: { color: colors.primary, fontSize: 13, fontWeight: '500' },
})
