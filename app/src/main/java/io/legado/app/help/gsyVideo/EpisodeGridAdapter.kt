package io.legado.app.help.gsyVideo

import android.content.Context
import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.widget.TextView
import androidx.recyclerview.widget.RecyclerView
import io.legado.app.R
import io.legado.app.lib.theme.accentColor

/**
 * 选集网格适配器（video-cache-and-multiep R7 / V4）。
 *
 * 取代历史 ListView 单列适配器（`SwitchVideoAdapter` 已随分组弹框退役删除）：
 * 样式统一由 [applyVideoChoiceItemStyle] 提供。
 *
 * book-info-unified-cache AD-05：新增**已缓存勾选角标**。
 * - `cachedFlags` 与 `titles` **同序**（由调用方按展示顺序换算好的布尔序列），
 *   因此倒序展示时角标跟随真实集号而非格子位置。
 *
 * @param currentSelection 组内当前集下标（-1 表示当前集不在本组）
 * @param cachedFlags 组内每格是否已缓存（与 `titles` 同序；默认空 = 不显示角标）
 * @param onItemClick 回调参数为**组内下标**（调用方负责叠加分组起点得到全集下标）
 */
class EpisodeGridAdapter(
    private val context: Context,
    private val titles: List<String>,
    private val currentSelection: Int,
    private val cachedFlags: List<Boolean> = emptyList(),
    private val onItemClick: (Int) -> Unit,
) : RecyclerView.Adapter<EpisodeGridAdapter.Holder>() {

    class Holder(val root: View, val textView: TextView, val badge: TextView) :
        RecyclerView.ViewHolder(root)

    override fun onCreateViewHolder(parent: ViewGroup, viewType: Int): Holder {
        val view = LayoutInflater.from(context)
            .inflate(R.layout.item_video_episode_chip, parent, false)
        val text = view.findViewById<TextView>(R.id.text1)
        val badge = view.findViewById<TextView>(R.id.episode_cached_badge)
        return Holder(view, text, badge)
    }

    override fun onBindViewHolder(holder: Holder, position: Int) {
        holder.textView.text = titles.getOrNull(position).orEmpty()
        applyVideoChoiceItemStyle(context, holder.textView, position == currentSelection)
        val cached = cachedFlags.getOrNull(position) == true
        holder.badge.visibility = if (cached) View.VISIBLE else View.GONE
        if (cached) holder.badge.setTextColor(context.accentColor)
        holder.textView.setOnClickListener { onItemClick(position) }
        holder.root.setOnClickListener { onItemClick(position) }
    }

    override fun getItemCount(): Int = titles.size
}
