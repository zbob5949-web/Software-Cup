import request from './request';

export interface LingshanWeather {
  location?: string;
  city?: string;
  weather?: string;
  temp?: string | number;
  tempMax?: string | number;
  temperature?: string | number;
  humidity?: string;
  feels_like?: string;
  suggestion?: string;
  advice?: string;
  icon?: string;
  updated_at?: string;
  error?: string;
}

const EMPTY_WEATHER: LingshanWeather = {
  location: '无锡灵山',
  weather: '暂无数据',
  temperature: '--',
};

/** Fetches the latest weather for Lingshan. */
export async function getLingshanWeather(): Promise<LingshanWeather> {
  const res = await request.get('/api/weather');
  const body = res.data as LingshanWeather & {
    code?: number;
    data?: LingshanWeather | null;
  };

  // The latest backend returns the weather object directly. Keep support for
  // the older { code, data } response so deployed backends can be upgraded
  // independently from the frontend.
  return body.data ?? (body.city || body.temperature || body.weather ? body : EMPTY_WEATHER);
}
