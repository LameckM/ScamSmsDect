import { View, Text, StyleSheet } from 'react-native'
import StatusPill from './StatusPill'
import { colors, spacing, radius, typography } from '../theme'

export default function RiskResultCard({ result }) {
  if (!result) return null

  return (
    <View style={styles.card}>
      <View style={styles.rowBetween}>
        <Text style={styles.sectionLabel}>This message</Text>
        <Text style={styles.score}>{result.message_score}/100</Text>
      </View>

      {result.flags.length > 0 ? (
        <View style={styles.flagRow}>
          {result.flags.map((flag) => (
            <View key={flag} style={styles.flagChip}>
              <Text style={styles.flagText}>{flag}</Text>
            </View>
          ))}
        </View>
      ) : (
        <Text style={styles.noFlags}>No scam indicators detected in this message.</Text>
      )}

      <View style={styles.divider} />

      <View style={styles.rowBetween}>
        <Text style={styles.sectionLabel}>This number overall</Text>
        <StatusPill status={result.status} />
      </View>
      <Text style={styles.summary}>
        {result.number} now has {result.report_count} report{result.report_count === 1 ? '' : 's'} and an
        aggregate risk score of {result.aggregate_score}/100.
      </Text>
    </View>
  )
}

const styles = StyleSheet.create({
  card: {
    backgroundColor: colors.surface,
    borderRadius: radius.lg,
    borderWidth: 1,
    borderColor: colors.border,
    padding: spacing.md,
    marginTop: spacing.md,
  },
  rowBetween: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: spacing.xs,
  },
  sectionLabel: { ...typography.label, color: colors.textMuted },
  score: { ...typography.subtitle, color: colors.textPrimary },
  flagRow: { flexDirection: 'row', flexWrap: 'wrap', marginTop: spacing.xs },
  flagChip: {
    backgroundColor: colors.primaryMuted,
    borderRadius: 999,
    paddingHorizontal: 10,
    paddingVertical: 4,
    marginRight: 6,
    marginBottom: 6,
  },
  flagText: { fontSize: 12, color: colors.primary, fontWeight: '500' },
  noFlags: { ...typography.body, color: colors.textSecondary, marginTop: spacing.xs },
  divider: { height: 1, backgroundColor: colors.border, marginVertical: spacing.sm },
  summary: { ...typography.body, color: colors.textSecondary, marginTop: spacing.xs, lineHeight: 20 },
})
