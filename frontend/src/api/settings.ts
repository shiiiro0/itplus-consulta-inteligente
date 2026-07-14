import client from './client'

export interface SettingItem {
  clave: string
  label: string
  unit: string
  help: string
  min: number
  max: number
  default: number
  valor: number
}

export async function getSettings(): Promise<SettingItem[]> {
  const { data } = await client.get<{ settings: SettingItem[] }>('/settings/')
  if (!data || !Array.isArray(data.settings)) {
    throw new Error('ENDPOINT_NO_DISPONIBLE')
  }
  return data.settings
}

export async function updateSettings(values: Record<string, number>): Promise<SettingItem[]> {
  const { data } = await client.put<{ ok: boolean; settings: SettingItem[] }>('/settings/', { values })
  return data.settings
}
