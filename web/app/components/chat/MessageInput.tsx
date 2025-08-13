interface MessageInputProps {
  value: string;
  onChange: (value: string) => void;
  onSend: () => void;
  onKeyPress: (e: React.KeyboardEvent) => void;
  disabled: boolean;
  placeholder: string;
}

export function MessageInput({
  value,
  onChange,
  onSend,
  onKeyPress,
  disabled,
  placeholder,
}: MessageInputProps) {
  return (
    <div className="flex space-x-2">
      <textarea
        value={value}
        onChange={(e) => onChange(e.target.value)}
        onKeyPress={onKeyPress}
        disabled={disabled}
        placeholder={placeholder}
        className="flex-1 resize-none rounded-lg border border-gray-300 px-4 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent disabled:bg-gray-100 disabled:cursor-not-allowed"
        rows={3}
      />
      <button
        onClick={onSend}
        disabled={disabled || !value.trim()}
        className="px-6 py-2 bg-blue-600 text-white rounded-lg font-medium hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 disabled:bg-gray-400 disabled:cursor-not-allowed transition-colors"
      >
        Send
      </button>
    </div>
  );
}
