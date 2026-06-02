/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import React, { useEffect, useRef } from 'react';
import {
  CandlestickSeries,
  ColorType,
  createChart,
  createSeriesMarkers,
  LineSeries,
  type IChartApi,
  type ISeriesApi,
  type ISeriesMarkersPluginApi,
} from 'lightweight-charts';
import { ScreenerDailyBarResponse, ScreenerMarkerResponse } from '@/services/api';

type Props = {
  bars: ScreenerDailyBarResponse[];
  markers?: ScreenerMarkerResponse[];
  height?: number;
};

export function PatternAChart({ bars, markers = [], height = 360 }: Props) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const candleRef = useRef<ISeriesApi<'Candlestick'> | null>(null);
  const ma5Ref = useRef<ISeriesApi<'Line'> | null>(null);
  const ma10Ref = useRef<ISeriesApi<'Line'> | null>(null);
  const ma20Ref = useRef<ISeriesApi<'Line'> | null>(null);
  const markersRef = useRef<ISeriesMarkersPluginApi<string> | null>(null);

  useEffect(() => {
    if (!containerRef.current) return;
    const chart = createChart(containerRef.current, {
      height,
      layout: {
        background: { type: ColorType.Solid, color: '#ffffff' },
        textColor: '#4B5563',
      },
      grid: {
        vertLines: { color: '#F3F4F6' },
        horzLines: { color: '#F3F4F6' },
      },
      rightPriceScale: { borderVisible: false },
      timeScale: { borderVisible: false },
    });
    const candleSeries = chart.addSeries(CandlestickSeries, {
      upColor: '#DC2626',
      downColor: '#16A34A',
      borderUpColor: '#DC2626',
      borderDownColor: '#16A34A',
      wickUpColor: '#DC2626',
      wickDownColor: '#16A34A',
    });
    const ma5 = chart.addSeries(LineSeries, { color: '#2563EB', lineWidth: 1 });
    const ma10 = chart.addSeries(LineSeries, { color: '#7C3AED', lineWidth: 1 });
    const ma20 = chart.addSeries(LineSeries, { color: '#D97706', lineWidth: 1 });

    chartRef.current = chart;
    candleRef.current = candleSeries;
    markersRef.current = createSeriesMarkers(candleSeries);
    ma5Ref.current = ma5;
    ma10Ref.current = ma10;
    ma20Ref.current = ma20;

    const resize = () => {
      if (containerRef.current) {
        chart.applyOptions({ width: containerRef.current.clientWidth });
      }
    };
    resize();
    window.addEventListener('resize', resize);

    return () => {
      window.removeEventListener('resize', resize);
      markersRef.current = null;
      chart.remove();
      chartRef.current = null;
    };
  }, [height]);

  useEffect(() => {
    if (!candleRef.current || !ma5Ref.current || !ma10Ref.current || !ma20Ref.current) return;
    candleRef.current.setData(
      bars.map((bar) => ({
        time: bar.tradeDate,
        open: bar.open,
        high: bar.high,
        low: bar.low,
        close: bar.close,
      })),
    );
    ma5Ref.current.setData(bars.filter((bar) => bar.ma5 !== null).map((bar) => ({ time: bar.tradeDate, value: bar.ma5 as number })));
    ma10Ref.current.setData(bars.filter((bar) => bar.ma10 !== null).map((bar) => ({ time: bar.tradeDate, value: bar.ma10 as number })));
    ma20Ref.current.setData(bars.filter((bar) => bar.ma20 !== null).map((bar) => ({ time: bar.tradeDate, value: bar.ma20 as number })));

    const keyMarker = markers.find((marker) => marker.kind === 'key_bearish');
    const confirmMarker = markers.find((marker) => marker.kind === 'confirm');
    const markersToShow = [keyMarker, confirmMarker].filter(Boolean) as ScreenerMarkerResponse[];
    markersRef.current?.setMarkers(
      markersToShow.map((marker) => ({
        time: marker.tradeDate,
        position: marker.kind === 'key_bearish' ? 'aboveBar' : 'belowBar',
        color: marker.kind === 'key_bearish' ? '#7F1D1D' : '#B45309',
        shape: marker.kind === 'key_bearish' ? 'arrowDown' : 'arrowUp',
        text: marker.label,
      })),
    );
    chartRef.current?.timeScale().fitContent();
  }, [bars, markers]);

  return (
    <div className="space-y-1">
      <div ref={containerRef} className="w-full" />
      <p className="text-[10px] text-gray-400 text-right">
        Charts by{' '}
        <a href="https://www.tradingview.com/lightweight-charts/" target="_blank" rel="noreferrer" className="underline">
          TradingView Lightweight Charts
        </a>
      </p>
    </div>
  );
}
