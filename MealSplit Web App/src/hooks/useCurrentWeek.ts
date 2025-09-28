import { useQuery } from '@tanstack/react-query';
import { planningAPI } from '../services/api';

export function useCurrentWeek() {
  return useQuery({
    queryKey: ['current-week'],
    queryFn: planningAPI.getCurrentWeek,
    staleTime: 5 * 60 * 1000, // 5 minutes
  });
}