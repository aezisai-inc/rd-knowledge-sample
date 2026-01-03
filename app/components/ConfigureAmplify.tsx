"use client";

import { useEffect } from "react";
import { configureAmplify } from "../lib/amplify-config";

/**
 * ConfigureAmplify - Amplify Gen2 設定コンポーネント
 *
 * アプリケーション起動時に Amplify を設定
 * amplify_outputs.json から自動的に設定を読み込む
 */
export function ConfigureAmplify() {
  useEffect(() => {
    configureAmplify();
  }, []);

  return null;
}
