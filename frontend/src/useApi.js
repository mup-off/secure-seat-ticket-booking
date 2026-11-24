import { useCallback, useEffect, useState } from 'react';
import { api } from './api.js';

// Loads data from the API; returns { data, error, reload }.
export function useApi(path) {
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);

  const reload = useCallback(() => {
    setError(null);
    return api.get(path).then(setData, setError);
  }, [path]);

  useEffect(() => {
    reload();
  }, [reload]);

  return { data, error, reload };
}
