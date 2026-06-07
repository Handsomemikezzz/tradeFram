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

/** 同花顺式日 K：固定柱宽、右侧留白、纵向留白，避免 fitContent 把蜡烛横向拉扁 */
const CHART_HEIGHT = 480;
const BAR_SPACING = 8;
const MIN_BAR_SPACING = 5;
const RIGHT_OFFSET = 12;
const PRICE_SCALE_MARGINS = { top: 0.12, bottom: 0.12 };

function applyDefaultVisibleRange(chart: IChartApi, barCount: number) {
  if (barCount <= 0) return;
  const timeScale = chart.timeScale();
  timeScale.setVisibleLogicalRange({
    from: Math.max(0, barCount - 125),
    to: barCount - 1 + RIGHT_OFFSET,
  });
}

type Props = {
  bars: ScreenerDailyBarResponse[];
  markers?: ScreenerMarkerResponse[];
  height?: number;
};

export function PatternAChart({ bars, markers = [], height = CHART_HEIGHT }: Props) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const candleRef = useRef<ISeriesApi<'Candlestick'> | null>(null);
  const ma5Ref = useRef<ISeriesApi<'Line'> | null>(null);
  const ma10Ref = useRef<ISeriesApi<'Line'> | null>(null);
  const ma20Ref = useRef<ISeriesApi<'Line'> | null>(null);
  const markersRef = useRef<ISeriesMarkersPluginApi<string> | null>(null);
  const barCountRef = useRef(0);

  useEffect(() => {
    barCountRef.current = bars.length;
  }, [bars.length]);

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
      rightPriceScale: {
        borderVisible: false,
        scaleMargins: PRICE_SCALE_MARGINS,
      },
      timeScale: {
        borderVisible: false,
        barSpacing: BAR_SPACING,
        minBarSpacing: MIN_BAR_SPACING,
        rightOffset: RIGHT_OFFSET,
        timeVisible: true,
        secondsVisible: false,
      },
      crosshair: {
        vertLine: { labelVisible: true },
        horzLine: { labelVisible: true },
      },
      handleScroll: {
        mouseWheel: true,
        pressedMouseMove: true,
        horzTouchDrag: true,
      },
      handleScale: {
        axisPressedMouseMove: { time: true, price: true },
        mouseWheel: true,
        pinch: true,
      },
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
        applyDefaultVisibleRange(chart, barCountRef.current);
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

    // Pattern A markers
    const keyMarker = markers.find((marker) => marker.kind === 'key_bearish');
    const confirmMarker = markers.find((marker) => marker.kind === 'confirm');
    // Uptrend markers
    const trendStartMarker = markers.find((marker) => marker.kind === 'trend_start');
    const recentHighMarker = markers.find((marker) => marker.kind === 'recent_high');
    const pullbackMarker = markers.find((marker) => marker.kind === 'pullback');

    const markersToShow = [
      keyMarker,
      confirmMarker,
      trendStartMarker,
      recentHighMarker,
      pullbackMarker,
    ].filter(Boolean) as ScreenerMarkerResponse[];

    markersRef.current?.setMarkers(
      markersToShow.map((marker) => {
        if (marker.kind === 'key_bearish') {
          return { time: marker.tradeDate, position: 'aboveBar' as const, color: '#7F1D1D', shape: 'arrowDown' as const, text: marker.label };
        }
        if (marker.kind === 'confirm') {
          return { time: marker.tradeDate, position: 'belowBar' as const, color: '#B45309', shape: 'arrowUp' as const, text: marker.label };
        }
        if (marker.kind === 'trend_start') {
          return { time: marker.tradeDate, position: 'belowBar' as const, color: '#059669', shape: 'circle' as const, text: marker.label };
        }
        if (marker.kind === 'recent_high') {
          return { time: marker.tradeDate, position: 'aboveBar' as const, color: '#D97706', shape: 'arrowDown' as const, text: marker.label };
        }
        if (marker.kind === 'pullback') {
          return { time: marker.tradeDate, position: 'belowBar' as const, color: '#2563EB', shape: 'arrowUp' as const, text: marker.label };
        }
        return { time: marker.tradeDate, position: 'belowBar' as const, color: '#6B7280', shape: 'circle' as const, text: marker.label };
      }),
    );
    if (chartRef.current) {
      applyDefaultVisibleRange(chartRef.current, bars.length);
    }
  }, [bars, markers]);


  return (
    <div className="space-y-1">
      <div ref={containerRef} className="w-full min-h-[480px]" />
      <p className="text-[10px] text-gray-400 text-right">
        Charts by{' '}
        <a href="https://www.tradingview.com/lightweight-charts/" target="_blank" rel="noreferrer" className="underline">
          TradingView Lightweight Charts
        </a>
      </p>
    </div>
  );
}
