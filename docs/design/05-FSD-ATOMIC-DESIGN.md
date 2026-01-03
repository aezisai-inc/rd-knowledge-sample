# FSD + Atomic Design フロントエンド設計

## 1. 設計概要

Feature-Sliced Design（FSD）と Atomic Design を組み合わせた
フロントエンドアーキテクチャ。

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         Frontend Architecture                                │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                    FSD (Feature-Sliced Design)                       │    │
│  │  機能スライス単位でのコード整理                                      │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                              +                                               │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                    Atomic Design                                     │    │
│  │  コンポーネントの階層的な整理                                        │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

## 2. FSD レイヤー構成

```
app/
├── (features)/         # Feature スライス
│   ├── memory/         # Memory 機能
│   ├── multimodal/     # Multimodal 機能
│   └── voice/          # Voice 機能
│
├── entities/           # ビジネスエンティティ
│   ├── session/
│   ├── memory/
│   └── agent/
│
├── shared/             # 共有コンポーネント
│   └── ui/             # Atomic Design
│
└── widgets/            # 複合ウィジェット
```

### レイヤー説明

| レイヤー | 説明 | 依存可能 |
|----------|------|----------|
| app | ルーティング、プロバイダー | entities, features, shared |
| widgets | 複合コンポーネント | entities, features, shared |
| features | 機能スライス | entities, shared |
| entities | ビジネスエンティティ | shared |
| shared | 共有リソース | なし |

## 3. Atomic Design 階層

```
shared/ui/
├── atoms/              # 最小単位
│   ├── Button/
│   ├── Input/
│   ├── Text/
│   └── Icon/
│
├── molecules/          # atoms の組み合わせ
│   ├── InputGroup/
│   ├── Card/
│   └── Badge/
│
├── organisms/          # 複雑な UI 部品
│   ├── ChatMessage/
│   ├── SessionList/
│   └── TestPanel/
│
└── templates/          # ページレイアウト
    ├── DashboardLayout/
    └── TestLayout/
```

## 4. Feature スライス構造

### Memory Feature

```
(features)/memory/
├── ui/                 # UI コンポーネント
│   ├── SessionCard.tsx
│   ├── EventList.tsx
│   └── SessionForm.tsx
│
├── model/              # 状態管理
│   ├── useSession.ts
│   ├── sessionStore.ts
│   └── types.ts
│
├── api/                # API 呼び出し
│   ├── mutations.ts
│   └── queries.ts
│
└── lib/                # ユーティリティ
    └── formatters.ts
```

### Multimodal Feature

```
(features)/multimodal/
├── ui/
│   ├── PromptInput.tsx
│   ├── ImagePreview.tsx
│   └── ResponseDisplay.tsx
│
├── model/
│   ├── useMultimodal.ts
│   └── types.ts
│
├── api/
│   └── mutations.ts
│
└── lib/
    └── imageUtils.ts
```

### Voice Feature

```
(features)/voice/
├── ui/
│   ├── VoiceRecorder.tsx
│   ├── TranscriptDisplay.tsx
│   └── AudioPlayer.tsx
│
├── model/
│   ├── useVoice.ts
│   └── types.ts
│
├── api/
│   └── mutations.ts
│
└── lib/
    └── audioUtils.ts
```

## 5. Atomic Design コンポーネント例

### Atoms

```tsx
// shared/ui/atoms/Button/Button.tsx
interface ButtonProps {
  variant: 'primary' | 'secondary' | 'danger';
  size: 'sm' | 'md' | 'lg';
  children: React.ReactNode;
  onClick?: () => void;
  disabled?: boolean;
}

export const Button: React.FC<ButtonProps> = ({
  variant = 'primary',
  size = 'md',
  children,
  ...props
}) => {
  return (
    <button
      className={cn(
        'rounded-md font-medium transition-colors',
        variants[variant],
        sizes[size],
      )}
      {...props}
    >
      {children}
    </button>
  );
};
```

### Molecules

```tsx
// shared/ui/molecules/InputGroup/InputGroup.tsx
interface InputGroupProps {
  label: string;
  error?: string;
  children: React.ReactNode;
}

export const InputGroup: React.FC<InputGroupProps> = ({
  label,
  error,
  children,
}) => {
  return (
    <div className="flex flex-col gap-1">
      <Text variant="label">{label}</Text>
      {children}
      {error && <Text variant="error">{error}</Text>}
    </div>
  );
};
```

### Organisms

```tsx
// shared/ui/organisms/ChatMessage/ChatMessage.tsx
interface ChatMessageProps {
  message: MemoryEvent;
}

export const ChatMessage: React.FC<ChatMessageProps> = ({ message }) => {
  const isUser = message.role === 'USER';
  
  return (
    <div className={cn(
      'flex gap-3',
      isUser ? 'flex-row-reverse' : 'flex-row',
    )}>
      <Avatar role={message.role} />
      <Card>
        <Text>{message.content}</Text>
        <Text variant="caption">{formatTimestamp(message.timestamp)}</Text>
      </Card>
    </div>
  );
};
```

### Templates

```tsx
// shared/ui/templates/DashboardLayout/DashboardLayout.tsx
interface DashboardLayoutProps {
  sidebar: React.ReactNode;
  main: React.ReactNode;
  header?: React.ReactNode;
}

export const DashboardLayout: React.FC<DashboardLayoutProps> = ({
  sidebar,
  main,
  header,
}) => {
  return (
    <div className="flex h-screen">
      <aside className="w-64 border-r">{sidebar}</aside>
      <div className="flex-1 flex flex-col">
        {header && <header className="h-16 border-b">{header}</header>}
        <main className="flex-1 overflow-auto">{main}</main>
      </div>
    </div>
  );
};
```

## 6. Widget 構成

```tsx
// widgets/TestDashboard/TestDashboard.tsx
export const TestDashboard: React.FC = () => {
  return (
    <DashboardLayout
      sidebar={<FeatureSelector />}
      header={<TestControls />}
      main={
        <div className="grid grid-cols-2 gap-4 p-4">
          <MemoryTestPanel />
          <MultimodalTestPanel />
          <VoiceTestPanel />
          <ResultsPanel />
        </div>
      }
    />
  );
};
```

## 7. 状態管理

### Apollo Client 統合

```tsx
// (features)/memory/api/queries.ts
import { gql, useQuery } from '@apollo/client';

const GET_SESSION = gql`
  query GetSession($sessionId: ID!) {
    getMemorySession(sessionId: $sessionId) {
      sessionId
      actorId
      sessionType
      startedAt
      endedAt
      eventCount
    }
  }
`;

export const useSession = (sessionId: string) => {
  return useQuery(GET_SESSION, {
    variables: { sessionId },
    skip: !sessionId,
  });
};
```

### Mutations

```tsx
// (features)/memory/api/mutations.ts
import { gql, useMutation } from '@apollo/client';

const CREATE_SESSION = gql`
  mutation CreateSession($input: CreateSessionInput!) {
    createMemorySession(title: $input.title, tags: $input.tags) {
      sessionId
      startedAt
    }
  }
`;

export const useCreateSession = () => {
  return useMutation(CREATE_SESSION, {
    refetchQueries: ['ListSessions'],
  });
};
```

## 8. ディレクトリ構造まとめ

```
app/
├── (features)/
│   ├── memory/
│   │   ├── ui/
│   │   ├── model/
│   │   ├── api/
│   │   └── lib/
│   ├── multimodal/
│   │   ├── ui/
│   │   ├── model/
│   │   ├── api/
│   │   └── lib/
│   └── voice/
│       ├── ui/
│       ├── model/
│       ├── api/
│       └── lib/
│
├── shared/
│   └── ui/
│       ├── atoms/
│       ├── molecules/
│       ├── organisms/
│       └── templates/
│
├── entities/
│   ├── session/
│   ├── memory/
│   ├── agent/
│   └── graph/
│
├── widgets/
│   ├── TestDashboard/
│   ├── ResultsComparison/
│   └── TestHistory/
│
├── amplify/
│   ├── data/
│   ├── functions/
│   └── backend.ts
│
└── layout.tsx
```

---

**作成日**: 2026-01-03
**更新日**: 2026-01-03
