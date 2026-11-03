import { View, Text, StyleSheet } from 'react-native'
import { colors } from '../theme'

const STATUS_STYLES = {
  monitoring: { bg: colors.primaryMuted, fg: colors.primary, label: 'Monitoring' },
  flagged: { bg: colors.warningMuted, fg: colors.warning, label: 'Flagged' },
  escalated: { bg: colors.dangerMuted, fg: colors.danger, label: 'Escalated' },
  cleared: { bg: colors.successMuted, fg: colors.success, label: 'Cleared' },
}

export default function StatusPill({ status }) {
  const style = STATUS_STYLES[status] || STATUS_STYLES.monitoring
  return (
    <View style={[styles.pill, { backgroundColor: style.bg }]}>
      <Text style={[styles.label, { color: style.fg }]}>{style.label}</Text>
    </View>
  )
}

const styles = StyleSheet.create({
  pill: {
    paddingHorizontal: 10,
    paddingVertical: 4,
    borderRadius: 999,
    alignSelf: 'flex-start',
  },
  label: { fontSize: 12, fontWeight: '600' },
})
